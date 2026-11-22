/* =========================================================================
   014 - SMART TRANSFER SUGGESTIONS + PROPHET-ONLY FORECAST VIEW (SQL Server)

   Chay file nay SAU database/03-migrations/013-users-permissions.sql.

   Noi dung:
     1. sp_Transfer_SuggestAI: so sanh du bao nhu cau (forecasts) voi ton kho
        (inventory) de goi y chuyen hang tu cua hang du thua sang cua hang thieu.
     2. sp_Forecasts_Latest: them tham so tuy chon @ModelName. Web chi hien
        ket qua mot hinh Prophet (thang 97/100 cap), nhung API van tra ve mo
        hinh neu client yeu cau (vi du xgboost) khi can doi chung.

   File giu ASCII (comment tieng Anh) de chay duoc tren Windows PowerShell.

   Chay: sqlcmd -S "LAPTOP-I39E3UT2\SQLEXPRESS" -U sa -P <mat_khau> -C \
                 -d spoilage_predictor -I -b -i database\03-migrations\014-smart-transfer.sql
   ========================================================================= */

SET QUOTED_IDENTIFIER ON;
SET ANSI_NULLS ON;
GO

/* -------------------------------------------------------------------------
   1. sp_Transfer_SuggestAI

   Y tuong: moi cap (cua hang, san pham) co hai con so
     - predicted_qty : tong nhu cầu du bao trong ca ky (30 ngay)
     - current_stock : ton kho that (cac lo con quantity > 0)
   Phan bo hieu suat bang "so ngay phu vu" = current_stock / nhu cau moi ngay.
   Mot cua hang du thua khi du phu vu hon muc tieu (@TargetDays), mot cua
   hang thieu hut khi thap hon muc tieu. So luong goi y la phan nho hon giua
   "luong du" va "luong thieu", nho nhat la yeu cau khong bi vuot qua kha
   nang that cua kho nguon.

   Vi sao khong dung ngung toi doi tuong (cua hang chi bi xet theo san pham
   co trong forecasts): chi 10 san pham co du bao, nen ket qua gioi han
   trong 10 san pham do - dung nhu du lieu hien co.

   Ket qua gom ca cac cot so hoc; router se viet phan `reason` bang tieng
   Viet de SQL khong phai chua chu co dau.
   ------------------------------------------------------------------------- */

CREATE OR ALTER PROCEDURE dbo.sp_Transfer_SuggestAI
    @TargetDays INT           = 14,
    @MinQty     DECIMAL(15,3) = 1,
    @Limit      INT           = 50,
    @ModelName  VARCHAR(50)   = 'prophet'
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        IF @TargetDays IS NULL OR @TargetDays <= 0 SET @TargetDays = 14;
        IF @MinQty IS NULL OR @MinQty < 0 SET @MinQty = 1;
        IF @Limit IS NULL OR @Limit <= 0 SET @Limit = 50;
        IF @Limit > 200 SET @Limit = 200;

        ;WITH demand AS (
            SELECT f.store_id,
                   f.product_id,
                   COUNT(DISTINCT f.forecast_date) AS horizon_days,
                   SUM(f.predicted_quantity)        AS predicted_qty,
                   MAX(f.model_name)                AS model_name
            FROM dbo.forecasts f
            WHERE (@ModelName IS NULL OR f.model_name = @ModelName)
            GROUP BY f.store_id, f.product_id
        ),
        stock AS (
            SELECT i.store_id, i.product_id, SUM(i.quantity) AS current_stock
            FROM dbo.inventory i
            WHERE i.quantity > 0
            GROUP BY i.store_id, i.product_id
        ),
        calc AS (
            SELECT d.store_id,
                   d.product_id,
                   d.model_name,
                   d.horizon_days,
                   d.predicted_qty,
                   ISNULL(s.current_stock, 0) AS current_stock,
                   CASE WHEN d.horizon_days > 0
                        THEN d.predicted_qty / d.horizon_days ELSE 0 END AS daily_demand
            FROM demand d
            LEFT JOIN stock s ON s.store_id = d.store_id AND s.product_id = d.product_id
        ),
        scored AS (
            SELECT c.*,
                   CASE WHEN c.daily_demand > 0
                        THEN c.current_stock / c.daily_demand ELSE 999999.0 END AS days_cover,
                   CAST(CASE WHEN c.daily_demand > 0
                             THEN c.current_stock - c.daily_demand * @TargetDays
                             ELSE c.current_stock END AS DECIMAL(15,3)) AS surplus_qty,
                   CAST(CASE WHEN c.daily_demand > 0
                             THEN c.daily_demand * @TargetDays - c.current_stock
                             ELSE 0 END AS DECIMAL(15,3)) AS shortage_qty
            FROM calc c
        ),
        surplus AS (
            SELECT sc.*,
                   ROW_NUMBER() OVER (
                       PARTITION BY sc.product_id ORDER BY sc.surplus_qty DESC
                   ) AS rn
            FROM scored sc
            WHERE sc.surplus_qty >= @MinQty
        ),
        shortage AS (
            SELECT sc.*,
                   ROW_NUMBER() OVER (
                       PARTITION BY sc.product_id ORDER BY sc.shortage_qty DESC
                   ) AS rn
            FROM scored sc
            WHERE sc.shortage_qty >= @MinQty
        )
        SELECT TOP (@Limit)
            sp.product_id,
            p.product_code,
            p.product_name,
            p.unit,
            sp.store_id        AS from_store_id,
            fs.store_code      AS from_store_code,
            fs.store_name      AS from_store_name,
            sh.store_id        AS to_store_id,
            ts.store_code      AS to_store_code,
            ts.store_name      AS to_store_name,
            sp.current_stock   AS from_stock,
            sp.predicted_qty   AS from_predicted_qty,
            sp.daily_demand    AS from_daily_demand,
            sp.days_cover      AS from_days_cover,
            sh.current_stock   AS to_stock,
            sh.predicted_qty   AS to_predicted_qty,
            sh.daily_demand    AS to_daily_demand,
            sh.days_cover      AS to_days_cover,
            sp.surplus_qty,
            sh.shortage_qty,
            CAST(CASE WHEN sp.surplus_qty < sh.shortage_qty
                      THEN sp.surplus_qty ELSE sh.shortage_qty END AS DECIMAL(15,3)) AS suggested_qty,
            sp.model_name,
            sp.horizon_days,
            @TargetDays AS target_days
        FROM surplus sp
        JOIN shortage sh ON sh.product_id = sp.product_id AND sh.rn = sp.rn
        JOIN dbo.products p ON p.product_id = sp.product_id
        JOIN dbo.stores fs ON fs.store_id = sp.store_id
        JOIN dbo.stores ts ON ts.store_id = sh.store_id
        ORDER BY (CASE WHEN sp.surplus_qty < sh.shortage_qty
                       THEN sp.surplus_qty ELSE sh.shortage_qty END) DESC;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

/* -------------------------------------------------------------------------
   2. sp_Forecasts_Latest: loc theo model (mac dinh NULL = giu hanh vi cu)

   Prophet la mo hinh chinh (thang 97/100 cap) nen giao dien web goi
   /forecasts/latest?model_name=prophet. Ba cap ma XGBoost thang van con
   trong bang de lam so doi chung trong bao cao, nhung khong hien tren web.
   ------------------------------------------------------------------------- */

CREATE OR ALTER PROCEDURE dbo.sp_Forecasts_Latest
    @StoreId   INT          = NULL,
    @ProductId INT          = NULL,
    @ModelName VARCHAR(50)  = NULL,
    @Page      INT          = 1,
    @PageSize  INT          = 20
AS
BEGIN
    SET NOCOUNT ON;
    IF @Page < 1 SET @Page = 1;
    IF @PageSize < 1 SET @PageSize = 20;
    IF @PageSize > 100 SET @PageSize = 100;
    DECLARE @Offset INT = (@Page - 1) * @PageSize;

    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        DECLARE @NewestDate DATE;
        SELECT @NewestDate = MAX(f.forecast_date)
        FROM dbo.forecasts f
        WHERE (@StoreId IS NULL OR f.store_id = @StoreId)
          AND (@ProductId IS NULL OR f.product_id = @ProductId)
          AND (@ModelName IS NULL OR f.model_name = @ModelName);

        ;WITH ranked AS (
            SELECT f.*,
                   ROW_NUMBER() OVER (
                       PARTITION BY f.store_id, f.product_id
                       ORDER BY CASE WHEN f.rmse IS NULL THEN 1 ELSE 0 END, f.rmse, f.forecast_id
                   ) AS rn
            FROM dbo.forecasts f
            WHERE f.forecast_date = @NewestDate
              AND (@StoreId IS NULL OR f.store_id = @StoreId)
              AND (@ProductId IS NULL OR f.product_id = @ProductId)
              AND (@ModelName IS NULL OR f.model_name = @ModelName)
        )
        SELECT COUNT(*) AS total FROM ranked WHERE rn = 1;

        ;WITH ranked AS (
            SELECT f.*,
                   ROW_NUMBER() OVER (
                       PARTITION BY f.store_id, f.product_id
                       ORDER BY CASE WHEN f.rmse IS NULL THEN 1 ELSE 0 END, f.rmse, f.forecast_id
                   ) AS rn
            FROM dbo.forecasts f
            WHERE f.forecast_date = @NewestDate
              AND (@StoreId IS NULL OR f.store_id = @StoreId)
              AND (@ProductId IS NULL OR f.product_id = @ProductId)
              AND (@ModelName IS NULL OR f.model_name = @ModelName)
        )
        SELECT r.store_id, r.product_id, r.model_name, r.forecast_date,
               r.predicted_quantity, r.lower_bound, r.upper_bound,
               r.recommended_import_qty,
               s.store_code, s.store_name,
               p.product_code, p.product_name
        FROM ranked r
        JOIN dbo.stores s ON s.store_id = r.store_id
        JOIN dbo.products p ON p.product_id = r.product_id
        WHERE r.rn = 1
        ORDER BY r.store_id, r.product_id
        OFFSET @Offset ROWS FETCH NEXT @PageSize ROWS ONLY;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO
