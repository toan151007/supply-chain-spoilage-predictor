/* =========================================================================
   015 - SPOILAGE RISK REPORT (SQL Server)

   Chay file nay SAU database/03-migrations/014-smart-transfer.sql.

   Noi dung:
     1. v_spoilage_risk        : view tinh rui ro hao hut cho tung lo hang.
     2. sp_Reports_SpoilageRisk: danh sach lo hang + diem rui ro cho bang chi tiet.
     3. sp_Reports_SpoilageSummary: 4 chi so KPI + du lieu bieu do + top lo rui ro.

   Cong thuc "Toc do ban du kien":
     - Uu tien du bao Prophet cua cap (cua hang, san pham):
           SUM(predicted_quantity) / COUNT(DISTINCT forecast_date)
     - Neu cap do KHONG co du bao (chi 10/50 san pham co du bao), dung toc do
       ban thuc te 30 ngay gan nhat (neo vao ngay ban hang cuoi cung, khong phai
       CURRENT_DATE) chia cho 30. Nho vay ca 1.333 lo hang deu co toc do ban,
       thay vi 80% lo bi coi la "khong ban duoc" chi vi thieu du bao.
     - Cot demand_source ghi ro dang dung nguon nao: forecast | sales | none.

   Cong thuc "Diem rui ro" (0-100):
     sellable  = daily_demand * days_left        (khong am)
     unsold    = max(quantity - sellable, 0)
     loss_ratio= unsold / quantity
     urgency   = 1 - min(max(days_left,0),30)/30
     score     = 100 * (0.7*loss_ratio + 0.3*urgency)
     Hang da het han => 100.
     >= 70: high (nguy co cao) | >= 40: warning (canh bao) | con lai: safe.

   "Gia tri that thoat" = unsold * unit_cost (hang da het han tinh toan bo).

   File giu ASCII (comment tieng Anh) de chay duoc tren Windows PowerShell.

   Chay: sqlcmd -S "LAPTOP-I39E3UT2\SQLEXPRESS" -U sa -P <mat_khau> -C \
                 -d spoilage_predictor -I -b -i database\03-migrations\015-spoilage-risk-report.sql
   ========================================================================= */

SET QUOTED_IDENTIFIER ON;
SET ANSI_NULLS ON;
GO

/* -------------------------------------------------------------------------
   1. v_spoilage_risk

   Mot dong cho moi lo hang con ton (quantity > 0, co expiry_date).
   View khong loc theo cua hang / nhom hang / so ngay: cac procedure tu loc,
   nho vay chi mot noi duy nhat chua cong thuc rui ro.
   ------------------------------------------------------------------------- */

CREATE OR ALTER VIEW dbo.v_spoilage_risk
AS
WITH anchor AS (
    /* Ngay ban hang cuoi cung co du lieu. Du lieu da duoc dong bo sang 2026
       nhung van neo vao ngay that de neu sau nay nap lai du lieu cu, toc do
       ban khong bi tut ve 0. */
    SELECT CAST(MAX(o.order_date) AS DATE) AS last_sale_date
    FROM dbo.orders o
    WHERE o.status = 'completed'
      AND o.order_type = 'sale'
),
demand_forecast AS (
    SELECT
        f.store_id,
        f.product_id,
        CAST(SUM(f.predicted_quantity) AS DECIMAL(18,4))
            / NULLIF(COUNT(DISTINCT f.forecast_date), 0) AS forecast_daily
    FROM dbo.forecasts f
    WHERE f.model_name = 'prophet'
    GROUP BY f.store_id, f.product_id
),
demand_sales AS (
    SELECT
        o.store_id,
        oi.product_id,
        CAST(SUM(oi.quantity) AS DECIMAL(18,4)) / 30.0 AS sales_daily
    FROM dbo.order_items oi
    JOIN dbo.orders o ON o.order_id = oi.order_id
    CROSS JOIN anchor a
    WHERE o.status = 'completed'
      AND o.order_type = 'sale'
      AND CAST(o.order_date AS DATE)
          BETWEEN DATEADD(DAY, -30, a.last_sale_date) AND a.last_sale_date
    GROUP BY o.store_id, oi.product_id
),
base AS (
    SELECT
        i.inventory_id,
        i.batch_code,
        i.expiry_date,
        CAST(i.quantity AS DECIMAL(18,3)) AS quantity,
        CAST(p.unit_cost AS DECIMAL(18,2)) AS unit_cost,
        CAST(i.quantity * p.unit_cost AS DECIMAL(18,2)) AS stock_value,
        DATEDIFF(DAY, CAST(SYSDATETIME() AS DATE), i.expiry_date) AS days_left,
        s.store_id,
        s.store_code,
        s.store_name,
        p.product_id,
        p.product_code,
        p.product_name,
        p.unit,
        c.category_id,
        c.category_name,
        ISNULL(df.forecast_daily, 0) AS forecast_daily,
        ISNULL(ds.sales_daily, 0) AS sales_daily,
        CASE WHEN df.forecast_daily IS NOT NULL THEN df.forecast_daily
             ELSE ISNULL(ds.sales_daily, 0) END AS daily_demand,
        CASE WHEN df.forecast_daily IS NOT NULL THEN 'forecast'
             WHEN ISNULL(ds.sales_daily, 0) > 0 THEN 'sales'
             ELSE 'none' END AS demand_source
    FROM dbo.inventory i
    JOIN dbo.products p ON p.product_id = i.product_id
    JOIN dbo.stores s   ON s.store_id = i.store_id
    LEFT JOIN dbo.categories c ON c.category_id = p.category_id
    LEFT JOIN demand_forecast df
           ON df.store_id = i.store_id AND df.product_id = i.product_id
    LEFT JOIN demand_sales ds
           ON ds.store_id = i.store_id AND ds.product_id = i.product_id
    WHERE i.quantity > 0
      AND i.expiry_date IS NOT NULL
),
scored AS (
    SELECT
        b.*,
        CASE
            WHEN b.days_left <= 0 THEN CAST(0 AS DECIMAL(18,4))
            WHEN b.daily_demand * b.days_left >= b.quantity THEN b.quantity
            ELSE CAST(b.daily_demand * b.days_left AS DECIMAL(18,4))
        END AS sellable_qty,
        CASE
            WHEN b.days_left <= 0 THEN b.quantity
            WHEN b.daily_demand * b.days_left >= b.quantity THEN CAST(0 AS DECIMAL(18,4))
            ELSE CAST(b.quantity - b.daily_demand * b.days_left AS DECIMAL(18,4))
        END AS unsold_qty
    FROM base b
),
risked AS (
    SELECT
        s.*,
        CAST(s.unsold_qty * s.unit_cost AS DECIMAL(18,2)) AS loss_value,
        CAST(
            CASE
                WHEN s.days_left < 0 THEN 100.0
                WHEN s.quantity <= 0 THEN 0.0
                ELSE 100.0 * (
                    0.7 * (s.unsold_qty / s.quantity)
                    + 0.3 * (
                        CASE
                            WHEN s.days_left >= 30 THEN 0.0
                            ELSE 1.0 - (CAST(s.days_left AS DECIMAL(10,4)) / 30.0)
                        END
                    )
                )
            END
        AS DECIMAL(5,1)) AS risk_score
    FROM scored s
)
SELECT
    r.inventory_id,
    r.batch_code,
    r.store_id,
    r.store_code,
    r.store_name,
    r.product_id,
    r.product_code,
    r.product_name,
    r.unit,
    r.category_id,
    r.category_name,
    r.quantity,
    r.unit_cost,
    r.stock_value,
    r.expiry_date,
    r.days_left,
    r.daily_demand,
    r.forecast_daily,
    r.sales_daily,
    r.demand_source,
    r.sellable_qty,
    r.unsold_qty,
    r.loss_value,
    r.risk_score,
    CASE
        WHEN r.risk_score >= 70 THEN 'high'
        WHEN r.risk_score >= 40 THEN 'warning'
        ELSE 'safe'
    END AS risk_level
FROM risked r;
GO


/* -------------------------------------------------------------------------
   2. sp_Reports_SpoilageRisk

   Bang chi tiet cua trang Bao cao. @Days la cua so han su dung tinh tu hom
   nay (0 = chi hang da het han / het han hom nay, 7, 30...). Hang da het han
   luon duoc tra ve vi days_left am <= moi @Days.
   ------------------------------------------------------------------------- */

CREATE OR ALTER PROCEDURE dbo.sp_Reports_SpoilageRisk
    @Days       INT = 30,
    @CategoryId INT = NULL,
    @StoreId    INT = NULL,
    @RiskLevel  VARCHAR(20) = NULL,
    @Limit      INT = 500
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        IF @Days IS NULL OR @Days < 0 SET @Days = 30;
        IF @Days > 365 SET @Days = 365;
        IF @Limit IS NULL OR @Limit <= 0 SET @Limit = 500;
        IF @Limit > 2000 SET @Limit = 2000;
        IF @RiskLevel IS NOT NULL AND @RiskLevel NOT IN ('safe', 'warning', 'high')
            SET @RiskLevel = NULL;

        SELECT TOP (@Limit)
            v.inventory_id,
            v.batch_code,
            v.store_id,
            v.store_code,
            v.store_name,
            v.product_id,
            v.product_code,
            v.product_name,
            v.unit,
            v.category_id,
            v.category_name,
            v.quantity,
            v.unit_cost,
            v.stock_value,
            v.expiry_date,
            v.days_left,
            v.daily_demand,
            v.demand_source,
            v.sellable_qty,
            v.unsold_qty,
            v.loss_value,
            v.risk_score,
            v.risk_level,
            CASE
                WHEN v.days_left <= 2 THEN 'inventory_check'
                WHEN v.days_left <= 7 THEN 'transfer'
                ELSE 'promotion'
            END AS recommended_action
        FROM dbo.v_spoilage_risk v
        WHERE v.days_left <= @Days
          AND (@CategoryId IS NULL OR v.category_id = @CategoryId)
          AND (@StoreId IS NULL OR v.store_id = @StoreId)
          AND (@RiskLevel IS NULL OR v.risk_level = @RiskLevel)
        ORDER BY v.risk_score DESC, v.loss_value DESC, v.days_left ASC;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO


/* -------------------------------------------------------------------------
   3. sp_Reports_SpoilageSummary

   Tra ve 4 result set:
     1. KPI: tong ton kho (ca scope), gia tri nguy co, ty le hao hut, so lo
        can xu ly, so lo het han, so lo nguy co cao.
     2. Bieu do cot chong: so lo safe/warning/high theo nhom hang.
     3. Bieu do duong: theo ngay het han (30 ngay truoc -> @Days toi),
        gia tri that thoat va ty le xu ly thanh cong.
     4. Top 5 lo rui ro nhat (du lieu cho phan Tom tat & Khuyen nghi AI).

   View duoc quet MOT lan vao #risk (1.333 dong) de 4 cau SELECT sau do chi
   doc bang tam, tranh quet lai order_items 4 lan.
   ------------------------------------------------------------------------- */

CREATE OR ALTER PROCEDURE dbo.sp_Reports_SpoilageSummary
    @Days       INT = 30,
    @CategoryId INT = NULL,
    @StoreId    INT = NULL
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        IF @Days IS NULL OR @Days < 0 SET @Days = 30;
        IF @Days > 365 SET @Days = 365;

        DECLARE @today DATE = CAST(SYSDATETIME() AS DATE);

        SELECT v.*
        INTO #risk
        FROM dbo.v_spoilage_risk v
        WHERE (@CategoryId IS NULL OR v.category_id = @CategoryId)
          AND (@StoreId IS NULL OR v.store_id = @StoreId);

        /* ---- 1. KPI ---------------------------------------------------- */
        SELECT
            k.total_stock_qty,
            k.total_stock_value,
            k.at_risk_qty,
            k.at_risk_value,
            CAST(
                CASE WHEN k.total_stock_value > 0
                     THEN 100.0 * k.at_risk_value / k.total_stock_value
                     ELSE 0 END
            AS DECIMAL(6,2)) AS spoilage_rate,
            k.lots_in_window,
            k.lots_to_handle,
            k.expired_lots,
            k.high_risk_lots,
            @Days AS window_days
        FROM (
            SELECT
                CAST(ISNULL(SUM(quantity), 0) AS DECIMAL(18,3)) AS total_stock_qty,
                CAST(ISNULL(SUM(stock_value), 0) AS DECIMAL(18,2)) AS total_stock_value,
                CAST(ISNULL(SUM(CASE WHEN days_left <= @Days THEN unsold_qty ELSE 0 END), 0)
                     AS DECIMAL(18,3)) AS at_risk_qty,
                CAST(ISNULL(SUM(CASE WHEN days_left <= @Days THEN loss_value ELSE 0 END), 0)
                     AS DECIMAL(18,2)) AS at_risk_value,
                ISNULL(SUM(CASE WHEN days_left <= @Days THEN 1 ELSE 0 END), 0) AS lots_in_window,
                ISNULL(SUM(CASE WHEN days_left <= @Days
                                  AND risk_level IN ('warning', 'high')
                                THEN 1 ELSE 0 END), 0) AS lots_to_handle,
                ISNULL(SUM(CASE WHEN days_left < 0 THEN 1 ELSE 0 END), 0) AS expired_lots,
                ISNULL(SUM(CASE WHEN days_left <= @Days
                                  AND risk_level = 'high'
                                THEN 1 ELSE 0 END), 0) AS high_risk_lots
            FROM #risk
        ) k;

        /* ---- 2. Cot chong theo nhom hang ------------------------------- */
        SELECT
            category_id,
            category_name,
            SUM(CASE WHEN risk_level = 'safe' THEN 1 ELSE 0 END) AS safe_count,
            SUM(CASE WHEN risk_level = 'warning' THEN 1 ELSE 0 END) AS warning_count,
            SUM(CASE WHEN risk_level = 'high' THEN 1 ELSE 0 END) AS high_count,
            CAST(SUM(CASE WHEN risk_level = 'safe' THEN stock_value ELSE 0 END)
                 AS DECIMAL(18,2)) AS safe_value,
            CAST(SUM(CASE WHEN risk_level = 'warning' THEN stock_value ELSE 0 END)
                 AS DECIMAL(18,2)) AS warning_value,
            CAST(SUM(CASE WHEN risk_level = 'high' THEN stock_value ELSE 0 END)
                 AS DECIMAL(18,2)) AS high_value
        FROM #risk
        WHERE days_left <= @Days
        GROUP BY category_id, category_name
        ORDER BY high_count DESC, warning_count DESC, category_name;

        /* ---- 3. Xu huong hao hut theo ngay het han ---------------------- */
        SELECT
            expiry_date AS trend_date,
            CAST(SUM(loss_value) AS DECIMAL(18,2)) AS loss_value,
            CAST(SUM(stock_value) AS DECIMAL(18,2)) AS total_value,
            COUNT(*) AS lot_count,
            CAST(
                CASE WHEN SUM(stock_value) > 0
                     THEN 100.0 * (1.0 - SUM(loss_value) / SUM(stock_value))
                     ELSE 100.0 END
            AS DECIMAL(6,2)) AS handled_rate
        FROM #risk
        WHERE days_left <= @Days
          AND expiry_date >= DATEADD(DAY, -30, @today)
        GROUP BY expiry_date
        ORDER BY expiry_date;

        /* ---- 4. Top lo rui ro ------------------------------------------ */
        SELECT TOP (5)
            product_name,
            product_code,
            store_name,
            batch_code,
            quantity,
            unit,
            days_left,
            risk_score,
            risk_level,
            loss_value
        FROM #risk
        WHERE days_left <= @Days
        ORDER BY risk_score DESC, loss_value DESC, days_left ASC;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO
