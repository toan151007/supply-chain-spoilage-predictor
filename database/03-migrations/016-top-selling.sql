/* =========================================================================
   016 - Top selling products report
   -------------------------------------------------------------------------
   Adds one read-only Stored Procedure:

     dbo.sp_Reports_TopSelling @Date

   Returns one row per product sold on that day:
     product_id, product_name, product_code, category_name,
     sale_date, total_quantity, total_revenue

   Rules:
   - Only completed sale orders count (status = 'completed',
     order_type = 'sale'); draft / cancelled / purchase orders are ignored.
   - Revenue is SUM(order_items.line_total), the generated column, so the
     number always matches the order detail the user sees.
   - @Date = NULL means "the latest date that actually has completed sales",
     so the web page opens on a day with data instead of an empty today.
   - Sorted by total_quantity DESC (best sellers first), then revenue.
   - Every procedure keeps the project standard: TRY/CATCH + TRANSACTION.
   ========================================================================= */

SET QUOTED_IDENTIFIER ON;
SET ANSI_NULLS ON;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Reports_TopSelling
    @Date DATE = NULL
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY
        IF @@TRANCOUNT = 0
            BEGIN TRANSACTION;

        /* Fall back to the latest day with real sales. The 2026 sync stops on
           20/11, so opening the page on "today" would otherwise look broken. */
        IF @Date IS NULL
        BEGIN
            SELECT @Date = CAST(MAX(o.order_date) AS DATE)
            FROM dbo.orders o
            WHERE o.status = 'completed'
              AND o.order_type = 'sale';
        END;

        IF @Date IS NULL
            SET @Date = CAST(SYSDATETIME() AS DATE);

        SELECT
            p.product_id,
            p.product_name,
            p.product_code,
            c.category_name,
            @Date AS sale_date,
            CAST(SUM(oi.quantity) AS DECIMAL(18,3)) AS total_quantity,
            CAST(SUM(oi.line_total) AS DECIMAL(18,2)) AS total_revenue
        FROM dbo.order_items oi
        JOIN dbo.orders o
          ON o.order_id = oi.order_id
        JOIN dbo.products p
          ON p.product_id = oi.product_id
        LEFT JOIN dbo.categories c
          ON c.category_id = p.category_id
        WHERE o.status = 'completed'
          AND o.order_type = 'sale'
          AND o.order_date >= @Date
          AND o.order_date < DATEADD(DAY, 1, @Date)
        GROUP BY
            p.product_id,
            p.product_name,
            p.product_code,
            c.category_name
        ORDER BY
            total_quantity DESC,
            total_revenue DESC,
            p.product_name;

        IF @@TRANCOUNT > 0
            COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;

        THROW;
    END CATCH
END;
GO
