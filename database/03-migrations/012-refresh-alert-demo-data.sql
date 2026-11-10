SET QUOTED_IDENTIFIER ON;
SET ANSI_NULLS ON;
GO

/* =========================================================================
   012 - DEMO DATA REFRESH + ALERT CLEANUP (10/11/2026)

   Problem: the demo seed was generated on 24/10/2026 and never moved, so
   every alert row kept created_at = 24/10/2026 while expiry dates drifted
   further into the past. The Alerts page then showed "expired 33 days ago"
   next to a creation date from October, which looks broken.

   This file adds two maintenance procedures:
     sp_Maintenance_RefreshInventoryDates
         Rewrites inventory expiry dates relative to today: some batches
         expired 3-5 days ago, some expire within the warning window, the
         rest stay fresh. A handful of (store, product) pairs are pushed
         below min_stock so the low_stock alert type is exercised. Finally
         every alert row is deleted so it can be regenerated.
     sp_Maintenance_FinalizeAlerts
         Drops over_stock alerts (the seed max_stock is not on the same
         scale as Kaggle demand - see AGENTS.md) and spreads created_at
         over the last three days so the timeline is plausible.

   Run order (scripts/refresh_alert_demo_data.py does step by step):
     1. EXEC dbo.sp_Maintenance_RefreshInventoryDates @WarningDays = 7
     2. EXEC dbo.sp_Alerts_Generate @WarningDays = 7
     3. EXEC dbo.sp_Maintenance_FinalizeAlerts
   ========================================================================= */

IF OBJECT_ID('dbo.sp_Maintenance_RefreshInventoryDates', 'P') IS NOT NULL
    DROP PROCEDURE dbo.sp_Maintenance_RefreshInventoryDates;
GO

CREATE PROCEDURE dbo.sp_Maintenance_RefreshInventoryDates
    @WarningDays   INT = 7,
    @LowStockPairs INT = 8
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @Today DATE = CAST(SYSDATETIME() AS DATE);
    DECLARE @DatesUpdated INT = 0;
    DECLARE @LowStockRowsTouched INT = 0;
    DECLARE @AlertsDeleted INT = 0;
    DECLARE @Spacing INT = 1;

    IF @WarningDays < 1 SET @WarningDays = 7;
    IF @LowStockPairs < 0 SET @LowStockPairs = 0;
    IF @LowStockPairs > 0
    BEGIN
        SET @Spacing = (500 / @LowStockPairs) + 1;
        IF @Spacing < 1 SET @Spacing = 1;
    END

    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        /* 1. Rewrite expiry dates relative to today.
           Groups are ranked once, so every batch of a (store, product) pair
           belongs to the same bucket; the per-batch shift keeps the
           (store_id, product_id, expiry_date) unique index satisfied. */
        UPDATE i
        SET expiry_date = DATEADD(DAY, p.offset_days, @Today),
            received_date = CASE
                WHEN DATEADD(DAY, p.offset_days - ISNULL(pr.shelf_life_days, 30), @Today) > @Today
                    THEN DATEADD(DAY, -(1 + ABS(p.offset_days) % 5), @Today)
                ELSE DATEADD(DAY, p.offset_days - ISNULL(pr.shelf_life_days, 30), @Today)
            END
        FROM dbo.inventory i
        JOIN (
            SELECT b.inventory_id,
                   b.product_id,
                   CASE b.group_no % 10
                       WHEN 0 THEN -(3 + ((b.group_no + b.batch_no) % 4))  /* expired 3-6 days ago */
                       WHEN 1 THEN 1 + b.group_no % 2 + (b.batch_no - 1)   /* expires in 1-5 days */
                       WHEN 2 THEN 8 + b.group_no % 6 + (b.batch_no - 1)   /* expires in 8-16 days */
                       WHEN 3 THEN 8 + b.group_no % 6 + (b.batch_no - 1)
                       ELSE 20 + (b.group_no * 7) % 80 + (b.batch_no - 1)  /* fresh 20-102 days */
                   END AS offset_days
            FROM (
                SELECT i2.inventory_id,
                       i2.store_id,
                       i2.product_id,
                       g.group_no,
                       ROW_NUMBER() OVER (
                           PARTITION BY i2.store_id, i2.product_id
                           ORDER BY i2.inventory_id
                       ) AS batch_no
                FROM dbo.inventory i2
                JOIN (
                    SELECT i3.store_id,
                           i3.product_id,
                           ROW_NUMBER() OVER (ORDER BY i3.store_id, i3.product_id) AS group_no
                    FROM dbo.inventory i3
                    GROUP BY i3.store_id, i3.product_id
                ) g
                  ON g.store_id = i2.store_id
                 AND g.product_id = i2.product_id
            ) b
        ) p ON p.inventory_id = i.inventory_id
        JOIN dbo.products pr ON pr.product_id = p.product_id;
        SET @DatesUpdated = @@ROWCOUNT;

        /* 2. Push a deterministic set of pairs below min_stock.
           Without this the low_stock alert type never fires, because the
           seed keeps 400-1000 units per pair while min_stock is 8-20. */
        IF @LowStockPairs > 0
        BEGIN
            DECLARE @Chosen TABLE (
                store_id INT NOT NULL,
                product_id INT NOT NULL,
                min_stock DECIMAL(18,3) NOT NULL
            );

            INSERT INTO @Chosen (store_id, product_id, min_stock)
            SELECT g.store_id, g.product_id, pr.min_stock
            FROM (
                SELECT i4.store_id,
                       i4.product_id,
                       ROW_NUMBER() OVER (ORDER BY i4.store_id, i4.product_id) AS group_no
                FROM dbo.inventory i4
                GROUP BY i4.store_id, i4.product_id
            ) g
            JOIN dbo.products pr ON pr.product_id = g.product_id
            WHERE g.group_no % @Spacing = 1;

            /* Re-running the script must not accumulate low-stock pairs.
               Any pair that is still below min_stock but is not chosen this
               time was zeroed by an earlier run, so lift it back above
               min_stock before applying the new selection. */
            UPDATE i
            SET quantity = CASE WHEN b.batch_no = 1 THEN b.min_stock * 8 ELSE 1 END
            FROM dbo.inventory i
            JOIN (
                SELECT i6.inventory_id,
                       pr6.min_stock,
                       ROW_NUMBER() OVER (
                           PARTITION BY i6.store_id, i6.product_id
                           ORDER BY i6.inventory_id
                       ) AS batch_no,
                       SUM(i6.quantity) OVER (
                           PARTITION BY i6.store_id, i6.product_id
                       ) AS pair_quantity
                FROM dbo.inventory i6
                JOIN dbo.products pr6 ON pr6.product_id = i6.product_id
            ) b ON b.inventory_id = i.inventory_id
            WHERE b.pair_quantity < b.min_stock
              AND NOT EXISTS (
                  SELECT 1
                  FROM @Chosen c
                  WHERE c.store_id = i.store_id
                    AND c.product_id = i.product_id
              );

            UPDATE i
            SET quantity = CASE
                WHEN b.batch_no = 1 THEN
                    CASE
                        WHEN b.min_stock - 1 - b.batch_count > 0
                            THEN b.min_stock - 1 - b.batch_count
                        ELSE 0
                    END
                ELSE 1
            END
            FROM dbo.inventory i
            JOIN (
                SELECT i5.inventory_id,
                       c.min_stock,
                       ROW_NUMBER() OVER (
                           PARTITION BY i5.store_id, i5.product_id
                           ORDER BY i5.inventory_id
                       ) AS batch_no,
                       COUNT(*) OVER (
                           PARTITION BY i5.store_id, i5.product_id
                       ) AS batch_count
                FROM dbo.inventory i5
                JOIN @Chosen c
                  ON c.store_id = i5.store_id
                 AND c.product_id = i5.product_id
            ) b ON b.inventory_id = i.inventory_id;
            SET @LowStockRowsTouched = @@ROWCOUNT;
        END

        /* Zero-quantity batches are demo artifacts left by an earlier run of
           this procedure. Real seed data never contains them, so lift them
           back to one unit to keep the inventory table readable. */
        UPDATE dbo.inventory SET quantity = 1 WHERE quantity = 0;

        /* 3. Wipe alerts so sp_Alerts_Generate can rebuild them. */
        DELETE FROM dbo.alerts;
        SET @AlertsDeleted = @@ROWCOUNT;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;

        SELECT @Today AS as_of_date,
               @DatesUpdated AS inventory_rows_updated,
               @LowStockRowsTouched AS low_stock_rows_reset,
               @AlertsDeleted AS alerts_deleted;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO


IF OBJECT_ID('dbo.sp_Maintenance_FinalizeAlerts', 'P') IS NOT NULL
    DROP PROCEDURE dbo.sp_Maintenance_FinalizeAlerts;
GO

CREATE PROCEDURE dbo.sp_Maintenance_FinalizeAlerts
    @SpreadMinutes INT = 4320
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @Now DATETIME2(7) = SYSDATETIME();
    DECLARE @OverStockDeleted INT = 0;
    DECLARE @TimestampsSpread INT = 0;

    IF @SpreadMinutes < 0 SET @SpreadMinutes = 0;

    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        /* max_stock in the seed is 40-100 while real demand is hundreds per
           day, so every pair would raise an over_stock alert. Those alerts
           are meaningless for the demo and only add noise. */
        DELETE FROM dbo.alerts WHERE alert_type = 'over_stock';
        SET @OverStockDeleted = @@ROWCOUNT;

        /* Keep created_at plausible in both directions:
             - expired rows: created a few hours AFTER the batch expired
               (an expiry alert cannot exist before the batch expires)
             - expiring-soon rows: created BEFORE the expiry date, spread
               over the last three days
           The MIN(@Now) guard keeps both branches in the past. */
        UPDATE dbo.alerts
        SET created_at = CASE
                WHEN alert_type = 'expired' AND expiry_date IS NOT NULL THEN
                    CASE
                        WHEN DATEADD(
                                HOUR,
                                4 + (CAST(alert_id AS BIGINT) * 7) % 20,
                                CAST(expiry_date AS DATETIME2(7))
                             ) > @Now
                            THEN DATEADD(MINUTE, -((CAST(alert_id AS BIGINT) * 11) % 240), @Now)
                        ELSE DATEADD(
                                HOUR,
                                4 + (CAST(alert_id AS BIGINT) * 7) % 20,
                                CAST(expiry_date AS DATETIME2(7))
                             )
                    END
                ELSE
                    DATEADD(
                        MINUTE,
                        -((CAST(alert_id AS BIGINT) * 37) % (@SpreadMinutes + 1)),
                        @Now
                    )
            END;
        SET @TimestampsSpread = @@ROWCOUNT;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;

        SELECT @OverStockDeleted AS over_stock_deleted,
               @TimestampsSpread AS timestamps_spread,
               @Now AS reference_time;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

PRINT 'Migration 012 applied: sp_Maintenance_RefreshInventoryDates, sp_Maintenance_FinalizeAlerts';
GO
