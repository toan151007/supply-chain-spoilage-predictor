/* =========================================================================
   017 - SMART TRANSFER: URGENCY + DISTANCE (SQL Server)

   Chay file nay SAU database/03-migrations/016-top-selling.sql.

   Noi dung:
     1. dbo.fn_StoreDistanceKm: khoang cach gia lap (km) giua hai cua hang,
        tinh co dinh tu store_id (schema khong luu toa do GPS).
     2. sp_Transfer_SuggestAI: them 2 cot transfer_urgency va distance_km,
        doi thu tu sap xep thanh: khan cap -> thieu nhieu -> gan truoc.

   File giu ASCII (comment tieng Anh) de chay duoc tren Windows PowerShell.

   Chay: sqlcmd -S "LAPTOP-I39E3UT2\SQLEXPRESS" -U sa -P <mat_khau> -C ^
                 -d spoilage_predictor -I -b ^
                 -i database\03-migrations\017-smart-transfer-urgency.sql
   ========================================================================= */

SET QUOTED_IDENTIFIER ON;
SET ANSI_NULLS ON;
GO

/* -------------------------------------------------------------------------
   1. fn_StoreDistanceKm

   Khoang cach duoc MO PHONG CO DINH tu store_id: moi cua hang nam tren mot
   luoi 5 cot x N hang, cach nhau 6 km theo chieu ngang va 9 km theo chieu
   doc, cong mot do lech nho theo id de khong co hai cap trung khoang cach.

   Ham deterministic (cung cap id luon ra cung mot so) de giao dien khong
   nhay so moi lan tai lai. Day la so lieu gia lap de xep thu tu uu tien,
   KHONG phai khoang cach thuc dia - phai noi ro khi viet bao cao.
   ------------------------------------------------------------------------- */

CREATE OR ALTER FUNCTION dbo.fn_StoreDistanceKm
    (@FromStoreId INT, @ToStoreId INT)
RETURNS DECIMAL(6,1)
AS
BEGIN
    IF @FromStoreId IS NULL OR @ToStoreId IS NULL RETURN NULL;
    IF @FromStoreId = @ToStoreId RETURN CAST(0 AS DECIMAL(6,1));

    -- Integer division on purpose: 0..4 is the column, 0.. is the row.
    DECLARE @fx DECIMAL(9,3) = ((@FromStoreId - 1) % 5) * 6.0
                              + ((@FromStoreId * 7) % 5) * 0.6;
    DECLARE @fy DECIMAL(9,3) = ((@FromStoreId - 1) / 5) * 9.0
                              + ((@FromStoreId * 3) % 4) * 0.5;
    DECLARE @tx DECIMAL(9,3) = ((@ToStoreId - 1) % 5) * 6.0
                              + ((@ToStoreId * 7) % 5) * 0.6;
    DECLARE @ty DECIMAL(9,3) = ((@ToStoreId - 1) / 5) * 9.0
                              + ((@ToStoreId * 3) % 4) * 0.5;

    RETURN CAST(ROUND(SQRT(SQUARE(@tx - @fx) + SQUARE(@ty - @fy)), 1)
                AS DECIMAL(6,1));
END;
GO

/* -------------------------------------------------------------------------
   2. sp_Transfer_SuggestAI

   Giu nguyen cach ghep cap (xep hang du thua / thieu hut trong tung san
   pham, ghep cung hang) va cach tinh so luong goi y. Chi them:

     transfer_urgency : muc khan cap theo so ngay phu cua cua hang NHAN
                        < 3 ngay = CRITICAL, 3..7 ngay = WARNING, con lai NORMAL
     distance_km      : khoang cach gia lap giua kho gui va kho nhan

   Thu tu sap xep moi: khan cap -> thieu nhieu -> gan truoc. Truoc day sap
   theo suggested_qty DESC, nen mot cap CRITICAL chi thieu 5 don vi co the
   nam duoi mot cap NORMAL thieu 900 don vi - sai ve nghiep vu.
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
            -- Urgency is about the RECEIVING store: how long it can still
            -- serve customers at the forecast demand rate.
            CAST(CASE WHEN sh.days_cover < 3 THEN 'CRITICAL'
                      WHEN sh.days_cover <= 7 THEN 'WARNING'
                      ELSE 'NORMAL' END AS VARCHAR(10)) AS transfer_urgency,
            dbo.fn_StoreDistanceKm(sp.store_id, sh.store_id) AS distance_km,
            sp.model_name,
            sp.horizon_days,
            @TargetDays AS target_days
        FROM surplus sp
        JOIN shortage sh ON sh.product_id = sp.product_id AND sh.rn = sp.rn
        JOIN dbo.products p ON p.product_id = sp.product_id
        JOIN dbo.stores fs ON fs.store_id = sp.store_id
        JOIN dbo.stores ts ON ts.store_id = sh.store_id
        ORDER BY
            CASE WHEN sh.days_cover < 3 THEN 0
                 WHEN sh.days_cover <= 7 THEN 1
                 ELSE 2 END ASC,
            sh.shortage_qty DESC,
            dbo.fn_StoreDistanceKm(sp.store_id, sh.store_id) ASC;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO
