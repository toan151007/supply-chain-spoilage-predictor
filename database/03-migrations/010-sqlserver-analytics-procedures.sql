/* =========================================================================
   SUPPLY CHAIN SPOILAGE PREDICTOR - ANALYTICS / REPORT / IMPORT PROCEDURES
   SQL Server 2025 Express, database spoilage_predictor.

   Migration 010. Adds the procedures that the dashboard, recommendation,
   report and import routers need. The 49 procedures in
   database/HUONG-DAN-CHAY-SSMS.md only cover CRUD; these cover the
   aggregate reads and the set-based import writes.

   Every procedure follows the project rules:
     - BEGIN TRY ... BEGIN CATCH
     - guarded transaction (IF @@TRANCOUNT = 0 ... COMMIT)
     - THROW 50001..50005 for business errors
   File is ASCII only.

   Error numbers (mapped to HTTP in backend/app/database.py):
     50001 NOT_FOUND      -> 404
     50002 DUPLICATE      -> 409
     50003 REFERENCED     -> 409
     50004 INVALID_STATE  -> 409
     50005 INVALID_INPUT  -> 422
   ========================================================================= */

SET QUOTED_IDENTIFIER ON;
SET ANSI_NULLS ON;
GO


/* =========================================================================
   1. DASHBOARD (B5)
   ========================================================================= */

CREATE OR ALTER PROCEDURE dbo.sp_Dashboard_Overview
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        DECLARE @total_revenue DECIMAL(18,2);
        DECLARE @total_orders INT;
        DECLARE @total_products INT;
        DECLARE @total_stores INT;
        DECLARE @total_inventory_value DECIMAL(18,2);
        DECLARE @total_alerts_unread INT;

        SELECT @total_revenue = ISNULL(SUM(total_amount), 0),
               @total_orders = COUNT(order_id)
        FROM dbo.orders;

        SELECT @total_products = COUNT(*) FROM dbo.products WHERE is_active = 1;
        SELECT @total_stores = COUNT(*) FROM dbo.stores WHERE is_active = 1;

        SELECT @total_inventory_value = ISNULL(SUM(total_stock_value), 0)
        FROM dbo.v_product_stock_summary;

        SELECT @total_alerts_unread = COUNT(*) FROM dbo.alerts WHERE is_read = 0;

        SELECT
            @total_revenue          AS total_revenue,
            @total_orders           AS total_orders,
            @total_products         AS total_products,
            @total_stores           AS total_stores,
            @total_inventory_value  AS total_inventory_value,
            @total_alerts_unread    AS total_alerts_unread;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO


CREATE OR ALTER PROCEDURE dbo.sp_Dashboard_Revenue
    @Period VARCHAR(10) = 'month',
    @Year   INT         = NULL
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        IF @Period NOT IN ('day', 'week', 'month', 'year')
            THROW 50005, 'Period must be one of: day, week, month, year', 1;

        SELECT
            b.period_start,
            ISNULL(SUM(o.total_amount), 0)   AS revenue,
            COUNT(o.order_id)                AS order_count,
            ISNULL(SUM(o.total_quantity), 0) AS total_quantity
        FROM dbo.orders o
        CROSS APPLY (
            SELECT CASE @Period
                WHEN 'day'   THEN CAST(o.order_date AS DATE)
                WHEN 'week'  THEN DATEADD(DAY,
                                    -(DATEDIFF(DAY, CONVERT(DATE, '19000101', 112),
                                               CAST(o.order_date AS DATE)) % 7),
                                    CAST(o.order_date AS DATE))
                WHEN 'month' THEN DATEFROMPARTS(YEAR(o.order_date), MONTH(o.order_date), 1)
                ELSE              DATEFROMPARTS(YEAR(o.order_date), 1, 1)
            END AS period_start
        ) b
        WHERE @Year IS NULL
           OR (o.order_date >= DATEFROMPARTS(@Year, 1, 1)
               AND o.order_date <  DATEFROMPARTS(@Year + 1, 1, 1))
        GROUP BY b.period_start
        ORDER BY b.period_start;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO


CREATE OR ALTER PROCEDURE dbo.sp_Dashboard_TopProducts
    @Limit   INT = 10,
    @StoreId INT = NULL,
    @Year    INT = NULL
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        IF @Limit < 1 OR @Limit > 100
            THROW 50005, 'Limit must be between 1 and 100', 1;

        SELECT TOP (@Limit)
            p.product_id,
            p.product_code,
            p.product_name,
            p.unit,
            ISNULL(SUM(oi.quantity), 0)   AS total_quantity,
            ISNULL(SUM(oi.line_total), 0) AS total_revenue
        FROM dbo.order_items oi
        JOIN dbo.orders o  ON o.order_id = oi.order_id
        JOIN dbo.products p ON p.product_id = oi.product_id
        WHERE o.order_type = 'sale'
          AND (@StoreId IS NULL OR o.store_id = @StoreId)
          AND (@Year IS NULL
               OR (o.order_date >= DATEFROMPARTS(@Year, 1, 1)
                   AND o.order_date <  DATEFROMPARTS(@Year + 1, 1, 1)))
        GROUP BY p.product_id, p.product_code, p.product_name, p.unit
        ORDER BY ISNULL(SUM(oi.quantity), 0) DESC;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO


CREATE OR ALTER PROCEDURE dbo.sp_Dashboard_LowStock
    @Threshold DECIMAL(15,3) = 20,
    @StoreId   INT           = NULL
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        SELECT
            store_id,
            product_id,
            product_code,
            product_name,
            unit,
            total_quantity,
            min_stock,
            reorder_point,
            shortage
        FROM dbo.v_low_stock
        WHERE shortage >= @Threshold
          AND (@StoreId IS NULL OR store_id = @StoreId)
        ORDER BY shortage DESC;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO


CREATE OR ALTER PROCEDURE dbo.sp_Dashboard_Expiring
    @Days      INT = 7,
    @StoreId   INT = NULL,
    @ProductId INT = NULL
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        IF @Days < 0 OR @Days > 30
            THROW 50005, 'Days must be between 0 and 30 (view window limit)', 1;

        SELECT
            inventory_id,
            store_id,
            product_id,
            product_code,
            product_name,
            batch_code,
            quantity,
            expiry_date,
            days_to_expiry,
            stock_value,
            alert_severity
        FROM dbo.v_expiring_inventory
        WHERE days_to_expiry <= @Days
          AND (@StoreId IS NULL OR store_id = @StoreId)
          AND (@ProductId IS NULL OR product_id = @ProductId)
        ORDER BY days_to_expiry;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO


CREATE OR ALTER PROCEDURE dbo.sp_Dashboard_AlertsSummary
    @StoreId INT = NULL
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        SELECT
            COUNT(alert_id)                                          AS total,
            ISNULL(SUM(CASE WHEN is_read = 0 THEN 1 ELSE 0 END), 0)  AS unread,
            ISNULL(SUM(CASE WHEN is_resolved = 0 THEN 1 ELSE 0 END), 0) AS unresolved,
            ISNULL(SUM(CASE WHEN is_read = 0 AND severity = 'critical'
                            THEN 1 ELSE 0 END), 0)                   AS critical_unread
        FROM dbo.alerts
        WHERE (@StoreId IS NULL OR store_id = @StoreId);

        SELECT
            alert_type,
            COUNT(alert_id)                                          AS total,
            ISNULL(SUM(CASE WHEN is_resolved = 0 THEN 1 ELSE 0 END), 0) AS unresolved
        FROM dbo.alerts
        WHERE (@StoreId IS NULL OR store_id = @StoreId)
        GROUP BY alert_type
        ORDER BY alert_type;

        SELECT severity, COUNT(alert_id) AS total
        FROM dbo.alerts
        WHERE (@StoreId IS NULL OR store_id = @StoreId)
        GROUP BY severity;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO


/* =========================================================================
   2. DASHBOARD ADVANCED (B8)
   ========================================================================= */

CREATE OR ALTER PROCEDURE dbo.sp_Dashboard_RevenueByStore
    @FromDate DATE = NULL,
    @ToDate   DATE = NULL,
    @Limit    INT  = NULL
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        SELECT TOP (CASE WHEN @Limit IS NULL THEN 2147483647 ELSE @Limit END)
            s.store_id,
            s.store_code,
            s.store_name,
            ISNULL(SUM(o.total_amount), 0)   AS total_revenue,
            COUNT(o.order_id)                AS total_orders,
            ISNULL(SUM(o.total_quantity), 0) AS total_quantity,
            CAST(CASE WHEN COUNT(o.order_id) = 0 THEN 0
                      ELSE ROUND(SUM(o.total_amount) / COUNT(o.order_id), 2)
                 END AS DECIMAL(18,2))       AS avg_order_value
        FROM dbo.stores s
        LEFT JOIN dbo.orders o
               ON o.store_id = s.store_id
              AND (@FromDate IS NULL OR o.order_date >= CAST(@FromDate AS DATETIME2))
              AND (@ToDate   IS NULL OR o.order_date <  DATEADD(DAY, 1, CAST(@ToDate AS DATETIME2)))
        GROUP BY s.store_id, s.store_code, s.store_name
        HAVING COUNT(o.order_id) > 0
        ORDER BY ISNULL(SUM(o.total_amount), 0) DESC;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO


CREATE OR ALTER PROCEDURE dbo.sp_Dashboard_RevenueByCategory
    @FromDate DATE = NULL,
    @ToDate   DATE = NULL
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        SELECT
            c.category_id,
            c.category_name,
            ISNULL(SUM(oi.line_total), 0) AS total_revenue,
            ISNULL(SUM(oi.quantity), 0)   AS total_quantity,
            COUNT(DISTINCT oi.product_id) AS product_count
        FROM dbo.order_items oi
        JOIN dbo.orders o   ON o.order_id = oi.order_id
        JOIN dbo.products p ON p.product_id = oi.product_id
        JOIN dbo.categories c ON c.category_id = p.category_id
        WHERE o.status = 'completed'
          AND o.order_type = 'sale'
          AND (@FromDate IS NULL OR o.order_date >= CAST(@FromDate AS DATETIME2))
          AND (@ToDate   IS NULL OR o.order_date <  DATEADD(DAY, 1, CAST(@ToDate AS DATETIME2)))
        GROUP BY c.category_id, c.category_name
        ORDER BY ISNULL(SUM(oi.line_total), 0) DESC;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO


CREATE OR ALTER PROCEDURE dbo.sp_Dashboard_InventoryValue
    @IncludeEmpty BIT = 0
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        DECLARE @horizon DATE = DATEADD(DAY, 30, CAST(SYSDATETIME() AS DATE));

        SELECT
            s.store_id,
            s.store_code,
            s.store_name,
            ISNULL(SUM(i.quantity), 0) AS total_items,
            COUNT(i.inventory_id)      AS total_batches,
            ISNULL(SUM(i.quantity * p.unit_cost), 0) AS total_value,
            ISNULL(SUM(CASE WHEN i.expiry_date IS NOT NULL
                             AND i.expiry_date <= @horizon
                            THEN i.quantity * p.unit_cost ELSE 0 END), 0) AS expiring_value
        FROM dbo.stores s
        LEFT JOIN dbo.inventory i
               ON i.store_id = s.store_id AND i.quantity > 0
        LEFT JOIN dbo.products p ON p.product_id = i.product_id
        GROUP BY s.store_id, s.store_code, s.store_name
        HAVING @IncludeEmpty = 1 OR ISNULL(SUM(i.quantity), 0) > 0
        ORDER BY ISNULL(SUM(i.quantity * p.unit_cost), 0) DESC;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO


CREATE OR ALTER PROCEDURE dbo.sp_Dashboard_WasteAnalysis
    @IncludeBatches BIT = 0,
    @Limit          INT = 50
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        DECLARE @today   DATE = CAST(SYSDATETIME() AS DATE);
        DECLARE @horizon DATE = DATEADD(DAY, 30, @today);

        /* ---- set 0: summary (worst case) ---- */
        SELECT
            ISNULL(SUM(CASE WHEN i.expiry_date < @today THEN 1 ELSE 0 END), 0) AS expired_batches,
            ISNULL(SUM(CASE WHEN i.expiry_date < @today THEN i.quantity ELSE 0 END), 0) AS expired_items,
            ISNULL(SUM(CASE WHEN i.expiry_date < @today
                            THEN i.quantity * p.unit_cost ELSE 0 END), 0) AS expired_value,
            ISNULL(SUM(CASE WHEN i.expiry_date >= @today THEN 1 ELSE 0 END), 0) AS expiring_batches,
            ISNULL(SUM(CASE WHEN i.expiry_date >= @today THEN i.quantity ELSE 0 END), 0) AS expiring_items,
            ISNULL(SUM(CASE WHEN i.expiry_date >= @today
                            THEN i.quantity * p.unit_cost ELSE 0 END), 0) AS expiring_value,
            ISNULL(SUM(i.quantity * p.unit_cost), 0) AS estimated_waste_value
        FROM dbo.inventory i
        JOIN dbo.products p ON p.product_id = i.product_id
        WHERE i.quantity > 0
          AND i.expiry_date IS NOT NULL
          AND i.expiry_date <= @horizon;

        /* ---- set 1: expired batches ---- */
        SELECT TOP (CASE WHEN @IncludeBatches = 1 THEN @Limit ELSE 0 END)
            i.inventory_id,
            i.store_id,
            s.store_name,
            i.product_id,
            p.product_code,
            p.product_name,
            i.expiry_date,
            DATEDIFF(DAY, @today, i.expiry_date) AS days_to_expiry,
            i.quantity,
            CAST(i.quantity * p.unit_cost AS DECIMAL(18,2)) AS value
        FROM dbo.inventory i
        JOIN dbo.stores s   ON s.store_id = i.store_id
        JOIN dbo.products p ON p.product_id = i.product_id
        WHERE i.quantity > 0
          AND i.expiry_date IS NOT NULL
          AND i.expiry_date < @today
        ORDER BY i.expiry_date;

        /* ---- set 2: batches expiring within the window ---- */
        SELECT TOP (CASE WHEN @IncludeBatches = 1 THEN @Limit ELSE 0 END)
            i.inventory_id,
            i.store_id,
            s.store_name,
            i.product_id,
            p.product_code,
            p.product_name,
            i.expiry_date,
            DATEDIFF(DAY, @today, i.expiry_date) AS days_to_expiry,
            i.quantity,
            CAST(i.quantity * p.unit_cost AS DECIMAL(18,2)) AS value
        FROM dbo.inventory i
        JOIN dbo.stores s   ON s.store_id = i.store_id
        JOIN dbo.products p ON p.product_id = i.product_id
        WHERE i.quantity > 0
          AND i.expiry_date IS NOT NULL
          AND i.expiry_date >= @today
          AND i.expiry_date <= @horizon
        ORDER BY i.expiry_date;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO


CREATE OR ALTER PROCEDURE dbo.sp_Dashboard_ForecastVsActual
    @ModelName     VARCHAR(50),
    @FromDate      DATE = NULL,
    @ToDate        DATE = NULL,
    @ProductId     INT  = NULL,
    @StoreId       INT  = NULL,
    @IncludeDetail BIT  = 0
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        DECLARE @fc_first DATE;
        DECLARE @fc_last  DATE;
        SELECT @fc_first = MIN(forecast_date), @fc_last = MAX(forecast_date)
        FROM dbo.forecasts
        WHERE model_name = @ModelName;

        DECLARE @actual_start DATE = @FromDate;
        DECLARE @actual_end   DATE = @ToDate;
        IF @fc_first IS NOT NULL
            SET @actual_start = CASE WHEN @actual_start IS NULL OR @actual_start < @fc_first
                                     THEN @fc_first ELSE @actual_start END;
        IF @fc_last IS NOT NULL
            SET @actual_end = CASE WHEN @actual_end IS NULL OR @actual_end > @fc_last
                                   THEN @fc_last ELSE @actual_end END;

        DECLARE @forecast_rows INT;
        SELECT @forecast_rows = COUNT(*)
        FROM dbo.forecasts
        WHERE model_name = @ModelName
          AND (@FromDate  IS NULL OR forecast_date >= @FromDate)
          AND (@ToDate    IS NULL OR forecast_date <= @ToDate)
          AND (@ProductId IS NULL OR product_id = @ProductId)
          AND (@StoreId   IS NULL OR store_id = @StoreId);

        DECLARE @actual_rows INT;
        SELECT @actual_rows = COUNT(*)
        FROM dbo.order_items oi
        JOIN dbo.orders o ON o.order_id = oi.order_id
        WHERE o.status = 'completed'
          AND o.order_type = 'sale'
          AND (@actual_start IS NULL OR o.order_date >= CAST(@actual_start AS DATETIME2))
          AND (@actual_end   IS NULL OR o.order_date <  DATEADD(DAY, 1, CAST(@actual_end AS DATETIME2)))
          AND (@ProductId IS NULL OR oi.product_id = @ProductId)
          AND (@StoreId   IS NULL OR o.store_id = @StoreId);

        /* Match on (store, product, day). Materialised once so the counts,
           the aggregates and the detail rows all read the same set. */
        CREATE TABLE #matched (
            store_id            INT           NOT NULL,
            product_id          INT           NOT NULL,
            forecast_date       DATE          NOT NULL,
            predicted_quantity  DECIMAL(15,3) NOT NULL,
            actual_quantity     DECIMAL(15,3) NOT NULL,
            err                 DECIMAL(18,3) NOT NULL,
            abs_err             DECIMAL(18,3) NOT NULL,
            pct_err             DECIMAL(18,6) NULL
        );

        INSERT INTO #matched
        SELECT
            f.store_id,
            f.product_id,
            f.forecast_date,
            f.predicted_quantity,
            oi.quantity,
            oi.quantity - f.predicted_quantity,
            ABS(oi.quantity - f.predicted_quantity),
            ABS(oi.quantity - f.predicted_quantity) / NULLIF(oi.quantity, 0) * 100
        FROM dbo.forecasts f
        JOIN dbo.orders o
               ON o.store_id = f.store_id
              AND CAST(o.order_date AS DATE) = f.forecast_date
              AND o.status = 'completed'
              AND o.order_type = 'sale'
        JOIN dbo.order_items oi
               ON oi.order_id = o.order_id
              AND oi.product_id = f.product_id
        WHERE f.model_name = @ModelName
          AND (@FromDate  IS NULL OR f.forecast_date >= @FromDate)
          AND (@ToDate    IS NULL OR f.forecast_date <= @ToDate)
          AND (@ProductId IS NULL OR f.product_id = @ProductId)
          AND (@StoreId   IS NULL OR f.store_id = @StoreId)
          AND (@actual_start IS NULL OR o.order_date >= CAST(@actual_start AS DATETIME2))
          AND (@actual_end   IS NULL OR o.order_date <  DATEADD(DAY, 1, CAST(@actual_end AS DATETIME2)));

        DECLARE @matched_rows INT = (SELECT COUNT(*) FROM #matched);

        /* ---- set 0: counts ---- */
        SELECT
            @forecast_rows AS forecast_rows,
            @actual_rows   AS actual_rows,
            @matched_rows  AS matched_rows,
            @fc_first      AS forecast_first_date,
            @fc_last       AS forecast_last_date;

        /* ---- set 1: accuracy ---- */
        SELECT
            AVG(pct_err)                                     AS mape,
            AVG(abs_err)                                     AS mae,
            AVG(err)                                         AS bias,
            ISNULL(SUM(err * err), 0)                        AS squared_error_sum,
            SUM(CASE WHEN actual_quantity = 0 THEN 1 ELSE 0 END) AS zero_actual_rows
        FROM #matched;

        /* ---- set 2: detail (capped) ---- */
        SELECT TOP (CASE WHEN @IncludeDetail = 1 THEN 200 ELSE 0 END)
            m.store_id,
            m.product_id,
            p.product_code,
            p.product_name,
            m.forecast_date,
            m.predicted_quantity,
            m.actual_quantity,
            m.err                AS error,
            ISNULL(m.pct_err, 0) AS abs_percentage_error
        FROM #matched m
        JOIN dbo.products p ON p.product_id = m.product_id
        ORDER BY m.forecast_date, m.store_id, m.product_id;

        DROP TABLE #matched;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF OBJECT_ID('tempdb..#matched') IS NOT NULL DROP TABLE #matched;
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO


/* =========================================================================
   3. RECOMMENDATIONS (B10)
   ========================================================================= */

CREATE OR ALTER PROCEDURE dbo.sp_Recommendations_Import
    @StoreId   INT           = NULL,
    @ProductId INT           = NULL,
    @MinQty    DECIMAL(15,3) = 0,
    @Limit     INT           = 200
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        DECLARE @today DATE = CAST(SYSDATETIME() AS DATE);
        DECLARE @risk  DATE = DATEADD(DAY, 30, @today);
        DECLARE @horizon_days INT;
        SELECT @horizon_days = DATEDIFF(DAY, MIN(forecast_date), MAX(forecast_date)) + 1
        FROM dbo.forecasts;
        IF @horizon_days IS NULL SET @horizon_days = 0;

        ;WITH demand AS (
            SELECT store_id, product_id,
                   SUM(predicted_quantity) AS predicted,
                   SUM(lower_bound)        AS lower_sum,
                   SUM(upper_bound)        AS upper_sum
            FROM dbo.forecasts
            GROUP BY store_id, product_id
        ),
        stock AS (
            SELECT store_id, product_id,
                   SUM(quantity) AS current_stock,
                   SUM(CASE WHEN expiry_date IS NOT NULL AND expiry_date <= @risk
                            THEN quantity ELSE 0 END) AS at_risk
            FROM dbo.inventory
            WHERE quantity > 0
            GROUP BY store_id, product_id
        ),
        calc AS (
            SELECT
                s.store_id,
                s.store_code,
                s.store_name,
                p.product_id,
                p.product_code,
                p.product_name,
                c.category_name,
                CAST(ISNULL(st.current_stock, 0) AS DECIMAL(15,3)) AS current_stock,
                CAST(ISNULL(st.at_risk, 0) AS DECIMAL(15,3))       AS expiring_stock,
                d.predicted,
                d.lower_sum,
                d.upper_sum,
                CAST(CASE WHEN p.reorder_point IS NOT NULL
                          THEN p.reorder_point ELSE p.min_stock END AS DECIMAL(15,3)) AS safety,
                @horizon_days AS horizon_days
            FROM demand d
            JOIN dbo.stores s   ON s.store_id = d.store_id
            JOIN dbo.products p ON p.product_id = d.product_id
            JOIN dbo.categories c ON c.category_id = p.category_id
            LEFT JOIN stock st  ON st.store_id = d.store_id AND st.product_id = d.product_id
            WHERE (@StoreId IS NULL OR d.store_id = @StoreId)
              AND (@ProductId IS NULL OR d.product_id = @ProductId)
        )
        SELECT TOP (@Limit)
            store_id, store_code, store_name,
            product_id, product_code, product_name, category_name,
            current_stock, expiring_stock, predicted AS predicted_demand,
            safety AS safety_stock,
            CAST(CASE
                WHEN predicted - (CASE WHEN current_stock - expiring_stock > 0
                                       THEN current_stock - expiring_stock ELSE 0 END) + safety > 0
                THEN predicted - (CASE WHEN current_stock - expiring_stock > 0
                                       THEN current_stock - expiring_stock ELSE 0 END) + safety
                ELSE 0 END AS DECIMAL(15,3)) AS recommended_import_qty,
            horizon_days,
            lower_sum,
            upper_sum
        FROM calc
        WHERE predicted - (CASE WHEN current_stock - expiring_stock > 0
                                THEN current_stock - expiring_stock ELSE 0 END) + safety > @MinQty
        ORDER BY recommended_import_qty DESC;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO


CREATE OR ALTER PROCEDURE dbo.sp_Recommendations_Expiring
    @Days      INT           = 7,
    @StoreId   INT           = NULL,
    @ProductId INT           = NULL,
    @MinValue  DECIMAL(18,2) = 0,
    @Limit     INT           = 200
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        DECLARE @today DATE = CAST(SYSDATETIME() AS DATE);
        DECLARE @cutoff DATE = DATEADD(DAY, @Days, @today);

        SELECT TOP (@Limit)
            i.inventory_id,
            i.store_id,
            s.store_code,
            s.store_name,
            i.product_id,
            p.product_code,
            p.product_name,
            i.expiry_date,
            DATEDIFF(DAY, @today, i.expiry_date) AS days_to_expiry,
            i.quantity,
            p.unit_cost AS unit_value,
            CAST(i.quantity * p.unit_cost AS DECIMAL(18,2)) AS total_value
        FROM dbo.inventory i
        JOIN dbo.stores s   ON s.store_id = i.store_id
        JOIN dbo.products p ON p.product_id = i.product_id
        WHERE i.quantity > 0
          AND i.expiry_date IS NOT NULL
          AND i.expiry_date <= @cutoff
          AND (@StoreId   IS NULL OR i.store_id = @StoreId)
          AND (@ProductId IS NULL OR i.product_id = @ProductId)
          AND CAST(i.quantity * p.unit_cost AS DECIMAL(18,2)) >= @MinValue
        ORDER BY total_value DESC;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO


CREATE OR ALTER PROCEDURE dbo.sp_Recommendations_SlowMoving
    @Days         INT           = 30,
    @StoreId      INT           = NULL,
    @MaxUnitsSold DECIMAL(15,3) = 5,
    @MinStock     DECIMAL(15,3) = 50,
    @Limit        INT           = 200
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        DECLARE @anchor DATE;
        SELECT @anchor = CAST(MAX(order_date) AS DATE)
        FROM dbo.orders
        WHERE status = 'completed' AND order_type = 'sale';
        IF @anchor IS NULL SET @anchor = CAST(SYSDATETIME() AS DATE);

        DECLARE @window_start DATE = DATEADD(DAY, -@Days, @anchor);
        DECLARE @window_end   DATE = DATEADD(DAY, 1, @anchor);

        ;WITH sold AS (
            SELECT o.store_id, oi.product_id,
                   SUM(oi.quantity) AS units
            FROM dbo.order_items oi
            JOIN dbo.orders o ON o.order_id = oi.order_id
            WHERE o.status = 'completed'
              AND o.order_type = 'sale'
              AND o.order_date >= CAST(@window_start AS DATETIME2)
              AND o.order_date <  CAST(@window_end AS DATETIME2)
            GROUP BY o.store_id, oi.product_id
        ),
        stock AS (
            SELECT store_id, product_id, SUM(quantity) AS current_stock
            FROM dbo.inventory
            WHERE quantity > 0
            GROUP BY store_id, product_id
        )
        SELECT TOP (@Limit)
            p.product_id,
            p.product_code,
            p.product_name,
            c.category_name,
            s.store_id,
            s.store_code,
            s.store_name,
            st.current_stock,
            CAST(st.current_stock * p.unit_cost AS DECIMAL(18,2)) AS stock_value,
            CAST(ISNULL(sold.units, 0) AS DECIMAL(15,3)) AS units_sold,
            @Days AS window_days
        FROM stock st
        JOIN dbo.products p ON p.product_id = st.product_id
        JOIN dbo.stores s   ON s.store_id = st.store_id
        JOIN dbo.categories c ON c.category_id = p.category_id
        LEFT JOIN sold ON sold.store_id = st.store_id AND sold.product_id = st.product_id
        WHERE st.current_stock >= @MinStock
          AND ISNULL(sold.units, 0) <= @MaxUnitsSold
          AND (@StoreId IS NULL OR st.store_id = @StoreId)
        ORDER BY stock_value DESC;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO


/* =========================================================================
   4. REPORTS (B11)
   ========================================================================= */

CREATE OR ALTER PROCEDURE dbo.sp_Reports_Inventory
    @StoreId     INT = NULL,
    @ProductId   INT = NULL,
    @CategoryId  INT = NULL,
    @InStockOnly BIT = 1,
    @Limit       INT = 50000
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        DECLARE @today DATE = CAST(SYSDATETIME() AS DATE);

        SELECT TOP (@Limit)
            i.inventory_id,
            s.store_code,
            s.store_name,
            p.product_code,
            p.product_name,
            c.category_name,
            i.batch_code,
            i.expiry_date,
            DATEDIFF(DAY, @today, i.expiry_date) AS days_left,
            i.quantity,
            p.unit_cost,
            CAST(i.quantity * p.unit_cost AS DECIMAL(18,2)) AS total_value,
            i.received_date
        FROM dbo.inventory i
        JOIN dbo.stores s   ON s.store_id = i.store_id
        JOIN dbo.products p ON p.product_id = i.product_id
        LEFT JOIN dbo.categories c ON c.category_id = p.category_id
        WHERE (@InStockOnly = 0 OR i.quantity > 0)
          AND (@StoreId    IS NULL OR i.store_id = @StoreId)
          AND (@ProductId  IS NULL OR i.product_id = @ProductId)
          AND (@CategoryId IS NULL OR p.category_id = @CategoryId)
        ORDER BY CASE WHEN i.expiry_date IS NULL THEN 1 ELSE 0 END, i.expiry_date;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO


CREATE OR ALTER PROCEDURE dbo.sp_Reports_Expiring
    @Days    INT = 30,
    @StoreId INT = NULL,
    @Limit   INT = 50000
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        IF @Days < 1 OR @Days > 30
            THROW 50005, 'Days must be between 1 and 30 (view window limit)', 1;

        DECLARE @today DATE = CAST(SYSDATETIME() AS DATE);
        DECLARE @cutoff DATE = DATEADD(DAY, @Days, @today);

        SELECT TOP (@Limit)
            i.inventory_id,
            s.store_code,
            s.store_name,
            p.product_code,
            p.product_name,
            i.batch_code,
            i.expiry_date,
            DATEDIFF(DAY, @today, i.expiry_date) AS days_left,
            i.quantity,
            p.unit_cost,
            CAST(i.quantity * p.unit_cost AS DECIMAL(18,2)) AS total_value
        FROM dbo.inventory i
        JOIN dbo.stores s   ON s.store_id = i.store_id
        JOIN dbo.products p ON p.product_id = i.product_id
        WHERE i.quantity > 0
          AND i.expiry_date IS NOT NULL
          AND i.expiry_date <= @cutoff
          AND (@StoreId IS NULL OR i.store_id = @StoreId)
        ORDER BY i.expiry_date;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO


CREATE OR ALTER PROCEDURE dbo.sp_Reports_Sales
    @FromDate   DATE = NULL,
    @ToDate     DATE = NULL,
    @StoreId    INT = NULL,
    @CategoryId INT = NULL,
    @GroupBy    VARCHAR(20) = 'day',
    @Limit      INT = 50000
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        IF @GroupBy NOT IN ('day', 'week', 'month', 'store', 'category', 'product')
            THROW 50005, 'GroupBy must be one of: day, week, month, store, category, product', 1;

        SELECT TOP (@Limit)
            b.bucket,
            COUNT(DISTINCT o.order_id)          AS orders,
            ISNULL(SUM(oi.quantity), 0)         AS quantity,
            ISNULL(SUM(oi.line_total), 0)       AS revenue
        FROM dbo.order_items oi
        JOIN dbo.orders o   ON o.order_id = oi.order_id
        JOIN dbo.stores s   ON s.store_id = o.store_id
        JOIN dbo.products p ON p.product_id = oi.product_id
        LEFT JOIN dbo.categories c ON c.category_id = p.category_id
        CROSS APPLY (
            SELECT CASE @GroupBy
                WHEN 'day'  THEN CONVERT(VARCHAR(10), CAST(o.order_date AS DATE), 23)
                WHEN 'week' THEN CONVERT(VARCHAR(10),
                                    DATEADD(DAY,
                                        -(DATEDIFF(DAY, CONVERT(DATE, '19000101', 112),
                                                   CAST(o.order_date AS DATE)) % 7),
                                        CAST(o.order_date AS DATE)), 23)
                WHEN 'month' THEN CONVERT(VARCHAR(7), o.order_date, 120)
                WHEN 'store' THEN s.store_code
                WHEN 'category' THEN ISNULL(c.category_name, N'')
                ELSE p.product_code
            END AS bucket
        ) b
        WHERE o.status = 'completed'
          AND o.order_type = 'sale'
          AND (@FromDate   IS NULL OR o.order_date >= CAST(@FromDate AS DATETIME2))
          AND (@ToDate     IS NULL OR o.order_date <  DATEADD(DAY, 1, CAST(@ToDate AS DATETIME2)))
          AND (@StoreId    IS NULL OR o.store_id = @StoreId)
          AND (@CategoryId IS NULL OR p.category_id = @CategoryId)
        GROUP BY b.bucket
        ORDER BY b.bucket;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO


CREATE OR ALTER PROCEDURE dbo.sp_Reports_Waste
    @Days    INT = 30,
    @StoreId INT = NULL,
    @Limit   INT = 50000
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        IF @Days < 1 OR @Days > 30
            THROW 50005, 'Days must be between 1 and 30 (view window limit)', 1;

        DECLARE @today DATE = CAST(SYSDATETIME() AS DATE);
        DECLARE @cutoff DATE = DATEADD(DAY, @Days, @today);

        SELECT TOP (@Limit)
            i.inventory_id,
            s.store_code,
            s.store_name,
            p.product_code,
            p.product_name,
            c.category_name,
            i.batch_code,
            i.expiry_date,
            DATEDIFF(DAY, @today, i.expiry_date) AS days_left,
            CASE WHEN i.expiry_date < @today THEN N'DA HET HAN'
                 ELSE N'SAP HET HAN' END AS state,
            i.quantity,
            p.unit_cost,
            CAST(i.quantity * p.unit_cost AS DECIMAL(18,2)) AS total_value
        FROM dbo.inventory i
        JOIN dbo.stores s   ON s.store_id = i.store_id
        JOIN dbo.products p ON p.product_id = i.product_id
        LEFT JOIN dbo.categories c ON c.category_id = p.category_id
        WHERE i.quantity > 0
          AND i.expiry_date IS NOT NULL
          AND i.expiry_date <= @cutoff
          AND (@StoreId IS NULL OR i.store_id = @StoreId)
        ORDER BY CASE WHEN i.expiry_date < @today THEN 0 ELSE 1 END,
                 CAST(i.quantity * p.unit_cost AS DECIMAL(18,2)) DESC;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO


/* =========================================================================
   5. IMPORT SUPPORT (B7)
   ========================================================================= */

CREATE OR ALTER PROCEDURE dbo.sp_Import_ReferenceIds
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        SELECT category_id FROM dbo.categories ORDER BY category_id;
        SELECT store_id FROM dbo.stores ORDER BY store_id;
        SELECT product_id FROM dbo.products ORDER BY product_id;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO


CREATE OR ALTER PROCEDURE dbo.sp_Import_CheckProductCodes
    @CodesJson NVARCHAR(MAX)
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        SELECT p.product_code
        FROM dbo.products p
        JOIN (SELECT value AS code FROM OPENJSON(@CodesJson)) j
          ON j.code = p.product_code;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO


CREATE OR ALTER PROCEDURE dbo.sp_Import_CheckInventoryLots
    @LotsJson NVARCHAR(MAX)
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        SELECT i.store_id, i.product_id, i.expiry_date
        FROM dbo.inventory i
        JOIN (
            SELECT store_id, product_id, expiry_date
            FROM OPENJSON(@LotsJson)
            WITH (
                store_id   INT  '$.store_id',
                product_id INT  '$.product_id',
                expiry_date DATE '$.expiry_date'
            )
        ) j
          ON j.store_id = i.store_id
         AND j.product_id = i.product_id
         AND j.expiry_date = i.expiry_date;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO


CREATE OR ALTER PROCEDURE dbo.sp_Import_CheckOrderCodes
    @CodesJson NVARCHAR(MAX)
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        SELECT o.order_code
        FROM dbo.orders o
        JOIN (SELECT value AS code FROM OPENJSON(@CodesJson)) j
          ON j.code = o.order_code;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO


CREATE OR ALTER PROCEDURE dbo.sp_Import_Products
    @RowsJson NVARCHAR(MAX)
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        DECLARE @ids TABLE (product_id INT NOT NULL);

        INSERT INTO dbo.products (
            product_code, product_name, category_id, unit,
            unit_cost, selling_price, shelf_life_days,
            min_stock, max_stock, supplier, is_perishable, is_active
        )
        OUTPUT INSERTED.product_id INTO @ids
        SELECT
            j.product_code, j.product_name, j.category_id, j.unit,
            j.unit_cost, j.selling_price, j.shelf_life_days,
            j.min_stock, j.max_stock, j.supplier, 1, 1
        FROM OPENJSON(@RowsJson)
        WITH (
            product_code    NVARCHAR(50)  '$.product_code',
            product_name    NVARCHAR(255) '$.product_name',
            category_id     INT           '$.category_id',
            unit            NVARCHAR(20)  '$.unit',
            unit_cost       DECIMAL(15,2) '$.unit_cost',
            selling_price   DECIMAL(15,2) '$.selling_price',
            shelf_life_days INT           '$.shelf_life_days',
            min_stock       DECIMAL(15,3) '$.min_stock',
            max_stock       DECIMAL(15,3) '$.max_stock',
            supplier        NVARCHAR(200) '$.supplier'
        ) j;

        SELECT product_id FROM @ids;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO


CREATE OR ALTER PROCEDURE dbo.sp_Import_Inventory
    @RowsJson NVARCHAR(MAX)
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        DECLARE @ids TABLE (inventory_id BIGINT NOT NULL);

        INSERT INTO dbo.inventory (
            store_id, product_id, quantity, expiry_date, batch_code, received_date
        )
        OUTPUT INSERTED.inventory_id INTO @ids
        SELECT
            j.store_id, j.product_id, j.quantity, j.expiry_date,
            j.batch_code, j.received_date
        FROM OPENJSON(@RowsJson)
        WITH (
            store_id      INT           '$.store_id',
            product_id    INT           '$.product_id',
            quantity      DECIMAL(15,3) '$.quantity',
            expiry_date   DATE          '$.expiry_date',
            batch_code    NVARCHAR(50)  '$.batch_code',
            received_date DATE          '$.received_date'
        ) j;

        SELECT inventory_id FROM @ids;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO


CREATE OR ALTER PROCEDURE dbo.sp_Import_Sales
    @OrdersJson NVARCHAR(MAX)
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        DECLARE @orders TABLE (
            order_id   BIGINT       NOT NULL,
            order_code NVARCHAR(50) NOT NULL
        );

        INSERT INTO dbo.orders (
            order_code, store_id, order_type, order_date, status,
            payment_method, customer_name, total_amount, total_quantity
        )
        OUTPUT INSERTED.order_id, INSERTED.order_code INTO @orders
        SELECT
            j.order_code, j.store_id, j.order_type, j.order_date, j.status,
            j.payment_method, j.customer_name, 0, 0
        FROM OPENJSON(@OrdersJson)
        WITH (
            order_code     NVARCHAR(50)  '$.order_code',
            order_date     DATETIME2(7)  '$.order_date',
            store_id       INT           '$.store_id',
            order_type     VARCHAR(20)   '$.order_type',
            status         VARCHAR(20)   '$.status',
            payment_method VARCHAR(30)   '$.payment_method',
            customer_name  NVARCHAR(150) '$.customer_name'
        ) j;

        INSERT INTO dbo.order_items (
            order_id, product_id, quantity, unit_price, unit_cost, discount_percent
        )
        SELECT
            t.order_id, l.product_id, l.quantity, l.unit_price, NULL, l.discount_percent
        FROM OPENJSON(@OrdersJson)
        WITH (
            order_code NVARCHAR(50) '$.order_code',
            lines      NVARCHAR(MAX) '$.lines' AS JSON
        ) o
        CROSS APPLY OPENJSON(o.lines)
        WITH (
            product_id       INT           '$.product_id',
            quantity         DECIMAL(15,3) '$.quantity',
            unit_price       DECIMAL(15,2) '$.unit_price',
            discount_percent DECIMAL(5,2)  '$.discount_percent'
        ) l
        JOIN @orders t ON t.order_code = o.order_code;

        UPDATE o
        SET o.total_amount   = x.total_amount,
            o.total_quantity = x.total_quantity
        FROM dbo.orders o
        JOIN (
            SELECT oi.order_id,
                   SUM(oi.line_total) AS total_amount,
                   SUM(oi.quantity)   AS total_quantity
            FROM dbo.order_items oi
            WHERE oi.order_id IN (SELECT order_id FROM @orders)
            GROUP BY oi.order_id
        ) x ON x.order_id = o.order_id;

        SELECT order_id FROM @orders;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

/* =========================================================================
   6. FIX: sp_Orders_Delete must remove its lines in the same transaction.
   The table already declares ON DELETE CASCADE, but the original procedure
   refused to delete while lines existed, which turned DELETE /orders/{id}
   into a 409 for every real order. Deleting the lines first restores the
   PostgreSQL behaviour without a second round trip from the API.
   ========================================================================= */

CREATE OR ALTER PROCEDURE dbo.sp_Orders_Delete
    @OrderId BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        IF NOT EXISTS (SELECT 1 FROM dbo.orders WHERE order_id = @OrderId)
            THROW 50001, N'Order not found', 1;

        DELETE FROM dbo.order_items WHERE order_id = @OrderId;
        DELETE FROM dbo.orders WHERE order_id = @OrderId;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO
