/* =========================================================================
   011 - STOCK TRANSFER WORKFLOW + SEASONAL FORECAST (SQL Server 2025)

   Chay file nay SAU database/HUONG-DAN-CHAY-SSMS.md va
   database/03-migrations/010-sqlserver-analytics-procedures.sql.

   Noi dung:
     1. Bang dbo.transfer_requests (yeu cau dieu chuyen hang giua cua hang)
     2. Mo rong CHECK reference_type cua inventory_transactions them 'transfer'
     3. Doi unique index uq_transactions_reference: them store_id
        (mot lan dieu chuyen tao 2 dong: xuat o kho nguon, nhap o kho dich)
     4. 10 Stored Procedure dieu chuyen (Create/Submit/Approve/Reject/Cancel/
        Ship/Complete/Get/List/Summary)
     5. 1 Stored Procedure du bao theo mua vu

   File giu ASCII. Ten mua tra ve duoi dang ma (spring/summer/autumn/winter),
   phan dich sang tieng Viet nam o backend/frontend.

   Chay: sqlcmd -S "LAPTOP-I39E3UT2\SQLEXPRESS" -U sa -P <mat_khau> -C \
                -d spoilage_predictor -I -i database\03-migrations\011-transfers-seasonal.sql
   ========================================================================= */

SET QUOTED_IDENTIFIER ON;
SET ANSI_NULLS ON;
GO

/* -------------------------------------------------------------------------
   1. transfer_requests
   ------------------------------------------------------------------------- */

IF OBJECT_ID(N'dbo.transfer_requests', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.transfer_requests (
        transfer_id    INT            IDENTITY(1,1) NOT NULL,
        transfer_code  NVARCHAR(30)   NOT NULL,
        from_store_id  INT            NOT NULL,
        to_store_id    INT            NOT NULL,
        product_id     INT            NOT NULL,
        quantity       DECIMAL(15,3)  NOT NULL,
        expiry_date    DATE           NULL,
        status         VARCHAR(20)    NOT NULL CONSTRAINT df_transfer_status DEFAULT ('proposed'),
        priority       VARCHAR(10)    NOT NULL CONSTRAINT df_transfer_priority DEFAULT ('normal'),
        reason         NVARCHAR(MAX)  NULL,
        note           NVARCHAR(MAX)  NULL,
        requested_by   INT            NULL,
        requested_at   DATETIME2(7)   NOT NULL CONSTRAINT df_transfer_requested_at DEFAULT (SYSDATETIME()),
        approved_by    INT            NULL,
        approved_at    DATETIME2(7)   NULL,
        rejected_by    INT            NULL,
        rejected_at    DATETIME2(7)   NULL,
        shipped_by     INT            NULL,
        shipped_at     DATETIME2(7)   NULL,
        received_by    INT            NULL,
        completed_at   DATETIME2(7)   NULL,
        created_at     DATETIME2(7)   NOT NULL CONSTRAINT df_transfer_created_at DEFAULT (SYSDATETIME()),
        updated_at     DATETIME2(7)   NOT NULL CONSTRAINT df_transfer_updated_at DEFAULT (SYSDATETIME()),
        CONSTRAINT pk_transfer_requests PRIMARY KEY (transfer_id),
        CONSTRAINT uq_transfer_requests_code UNIQUE (transfer_code),
        CONSTRAINT fk_transfer_from_store FOREIGN KEY (from_store_id)
            REFERENCES dbo.stores (store_id),
        CONSTRAINT fk_transfer_to_store FOREIGN KEY (to_store_id)
            REFERENCES dbo.stores (store_id),
        CONSTRAINT fk_transfer_product FOREIGN KEY (product_id)
            REFERENCES dbo.products (product_id),
        /* SQL Server rejects several cascade paths from users to the same
           table (error 1785), so the audit columns use NO ACTION. There is no
           user-deletion endpoint today; if one is added it must clear these
           columns explicitly first, because the history must keep its actor. */
        CONSTRAINT fk_transfer_requested_by FOREIGN KEY (requested_by)
            REFERENCES dbo.users (user_id),
        CONSTRAINT fk_transfer_approved_by FOREIGN KEY (approved_by)
            REFERENCES dbo.users (user_id),
        CONSTRAINT fk_transfer_rejected_by FOREIGN KEY (rejected_by)
            REFERENCES dbo.users (user_id),
        CONSTRAINT fk_transfer_shipped_by FOREIGN KEY (shipped_by)
            REFERENCES dbo.users (user_id),
        CONSTRAINT fk_transfer_received_by FOREIGN KEY (received_by)
            REFERENCES dbo.users (user_id),
        CONSTRAINT chk_transfer_quantity CHECK (quantity > 0),
        CONSTRAINT chk_transfer_stores CHECK (from_store_id <> to_store_id),
        CONSTRAINT chk_transfer_status CHECK (
            status IN ('proposed', 'pending', 'approved', 'in_transit', 'received', 'rejected', 'cancelled')
        ),
        CONSTRAINT chk_transfer_priority CHECK (priority IN ('low', 'normal', 'high', 'urgent'))
    );
END
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = N'ix_transfer_status' AND object_id = OBJECT_ID(N'dbo.transfer_requests')
)
    CREATE INDEX ix_transfer_status ON dbo.transfer_requests (status, requested_at DESC);
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = N'ix_transfer_stores' AND object_id = OBJECT_ID(N'dbo.transfer_requests')
)
    CREATE INDEX ix_transfer_stores ON dbo.transfer_requests (from_store_id, to_store_id);
GO

/* -------------------------------------------------------------------------
   2. inventory_transactions: allow reference_type = 'transfer'
   ------------------------------------------------------------------------- */

IF EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = N'chk_inv_tx_reference_type')
BEGIN
    ALTER TABLE dbo.inventory_transactions DROP CONSTRAINT chk_inv_tx_reference_type;
END
GO

ALTER TABLE dbo.inventory_transactions ADD CONSTRAINT chk_inv_tx_reference_type
    CHECK (reference_type IN ('manual', 'order', 'import_excel', 'transfer'));
GO

/* -------------------------------------------------------------------------
   3. uq_transactions_reference: add store_id

   Mot lan dieu chuyen sinh 2 dong inventory_transactions cung
   (reference_type='transfer', reference_id, product_id, expiry_date) nhung
   khac store_id (xuat o kho nguon, nhap o kho dich). Index cu thieu
   store_id nen dong nhap se bi coi la trung va bi tu choi.
   ------------------------------------------------------------------------- */

IF EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = N'uq_transactions_reference' AND object_id = OBJECT_ID(N'dbo.inventory_transactions')
)
    DROP INDEX uq_transactions_reference ON dbo.inventory_transactions;
GO

CREATE UNIQUE INDEX uq_transactions_reference
    ON dbo.inventory_transactions (reference_type, reference_id, store_id, product_id, expiry_date)
    WHERE reference_id IS NOT NULL AND expiry_date IS NOT NULL;
GO

/* -------------------------------------------------------------------------
   4. Stored Procedures - dieu chuyen hang

   Status machine:
       proposed  -> pending -> approved -> in_transit -> received
       proposed|pending -> cancelled
       proposed|pending -> rejected
   ------------------------------------------------------------------------- */

CREATE OR ALTER PROCEDURE dbo.sp_Transfer_Get
    @TransferId INT
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        IF NOT EXISTS (SELECT 1 FROM dbo.transfer_requests WHERE transfer_id = @TransferId)
            THROW 50001, N'Transfer request not found', 1;

        SELECT
            t.transfer_id,
            t.transfer_code,
            t.from_store_id,
            fs.store_code AS from_store_code,
            fs.store_name AS from_store_name,
            t.to_store_id,
            ts.store_code AS to_store_code,
            ts.store_name AS to_store_name,
            t.product_id,
            p.product_code,
            p.product_name,
            p.unit,
            c.category_name,
            t.quantity,
            t.expiry_date,
            t.status,
            t.priority,
            t.reason,
            t.note,
            t.requested_at,
            t.approved_at,
            t.rejected_at,
            t.shipped_at,
            t.completed_at,
            ru.full_name AS requested_by_name,
            au.full_name AS approved_by_name,
            xu.full_name AS rejected_by_name,
            su.full_name AS shipped_by_name,
            cu.full_name AS received_by_name
        FROM dbo.transfer_requests t
        JOIN dbo.stores fs ON fs.store_id = t.from_store_id
        JOIN dbo.stores ts ON ts.store_id = t.to_store_id
        JOIN dbo.products p ON p.product_id = t.product_id
        JOIN dbo.categories c ON c.category_id = p.category_id
        LEFT JOIN dbo.users ru ON ru.user_id = t.requested_by
        LEFT JOIN dbo.users au ON au.user_id = t.approved_by
        LEFT JOIN dbo.users xu ON xu.user_id = t.rejected_by
        LEFT JOIN dbo.users su ON su.user_id = t.shipped_by
        LEFT JOIN dbo.users cu ON cu.user_id = t.received_by
        WHERE t.transfer_id = @TransferId;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Transfer_List
    @Status      VARCHAR(20)   = NULL,
    @FromStoreId INT           = NULL,
    @ToStoreId   INT           = NULL,
    @ProductId   INT           = NULL,
    @Search      NVARCHAR(255) = NULL,
    @Page        INT           = 1,
    @PageSize    INT           = 20
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        IF @Page IS NULL OR @Page < 1 SET @Page = 1;
        IF @PageSize IS NULL OR @PageSize < 1 SET @PageSize = 20;
        IF @PageSize > 100 SET @PageSize = 100;
        IF @Status IS NOT NULL AND @Status NOT IN
            ('proposed', 'pending', 'approved', 'in_transit', 'received', 'rejected', 'cancelled')
            THROW 50005, N'status is not valid', 1;

        DECLARE @Offset INT = (@Page - 1) * @PageSize;

        SELECT COUNT(*) AS total
        FROM dbo.transfer_requests t
        JOIN dbo.stores fs ON fs.store_id = t.from_store_id
        JOIN dbo.stores ts ON ts.store_id = t.to_store_id
        JOIN dbo.products p ON p.product_id = t.product_id
        WHERE (@Status IS NULL OR t.status = @Status)
          AND (@FromStoreId IS NULL OR t.from_store_id = @FromStoreId)
          AND (@ToStoreId IS NULL OR t.to_store_id = @ToStoreId)
          AND (@ProductId IS NULL OR t.product_id = @ProductId)
          AND (@Search IS NULL
               OR t.transfer_code LIKE N'%' + @Search + N'%'
               OR p.product_name LIKE N'%' + @Search + N'%'
               OR p.product_code LIKE N'%' + @Search + N'%'
               OR fs.store_name LIKE N'%' + @Search + N'%'
               OR ts.store_name LIKE N'%' + @Search + N'%');

        SELECT
            t.transfer_id,
            t.transfer_code,
            t.from_store_id,
            fs.store_code AS from_store_code,
            fs.store_name AS from_store_name,
            t.to_store_id,
            ts.store_code AS to_store_code,
            ts.store_name AS to_store_name,
            t.product_id,
            p.product_code,
            p.product_name,
            p.unit,
            c.category_name,
            t.quantity,
            t.expiry_date,
            t.status,
            t.priority,
            t.reason,
            t.note,
            t.requested_at,
            t.approved_at,
            t.rejected_at,
            t.shipped_at,
            t.completed_at,
            ru.full_name AS requested_by_name,
            au.full_name AS approved_by_name,
            xu.full_name AS rejected_by_name,
            su.full_name AS shipped_by_name,
            cu.full_name AS received_by_name
        FROM dbo.transfer_requests t
        JOIN dbo.stores fs ON fs.store_id = t.from_store_id
        JOIN dbo.stores ts ON ts.store_id = t.to_store_id
        JOIN dbo.products p ON p.product_id = t.product_id
        JOIN dbo.categories c ON c.category_id = p.category_id
        LEFT JOIN dbo.users ru ON ru.user_id = t.requested_by
        LEFT JOIN dbo.users au ON au.user_id = t.approved_by
        LEFT JOIN dbo.users xu ON xu.user_id = t.rejected_by
        LEFT JOIN dbo.users su ON su.user_id = t.shipped_by
        LEFT JOIN dbo.users cu ON cu.user_id = t.received_by
        WHERE (@Status IS NULL OR t.status = @Status)
          AND (@FromStoreId IS NULL OR t.from_store_id = @FromStoreId)
          AND (@ToStoreId IS NULL OR t.to_store_id = @ToStoreId)
          AND (@ProductId IS NULL OR t.product_id = @ProductId)
          AND (@Search IS NULL
               OR t.transfer_code LIKE N'%' + @Search + N'%'
               OR p.product_name LIKE N'%' + @Search + N'%'
               OR p.product_code LIKE N'%' + @Search + N'%'
               OR fs.store_name LIKE N'%' + @Search + N'%'
               OR ts.store_name LIKE N'%' + @Search + N'%')
        ORDER BY
            CASE t.status
                WHEN 'pending' THEN 1
                WHEN 'approved' THEN 2
                WHEN 'in_transit' THEN 3
                WHEN 'proposed' THEN 4
                WHEN 'received' THEN 5
                ELSE 6
            END,
            t.requested_at DESC,
            t.transfer_id DESC
        OFFSET @Offset ROWS FETCH NEXT @PageSize ROWS ONLY;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Transfer_Create
    @FromStoreId INT,
    @ToStoreId   INT,
    @ProductId   INT,
    @Quantity    DECIMAL(15,3),
    @ExpiryDate  DATE          = NULL,
    @Priority    VARCHAR(10)   = 'normal',
    @Reason      NVARCHAR(MAX) = NULL,
    @Note        NVARCHAR(MAX) = NULL,
    @RequestedBy INT           = NULL
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        IF @FromStoreId IS NULL OR NOT EXISTS
            (SELECT 1 FROM dbo.stores WHERE store_id = @FromStoreId)
            THROW 50005, N'from_store_id does not exist', 1;
        IF @ToStoreId IS NULL OR NOT EXISTS
            (SELECT 1 FROM dbo.stores WHERE store_id = @ToStoreId)
            THROW 50005, N'to_store_id does not exist', 1;
        IF @FromStoreId = @ToStoreId
            THROW 50005, N'from_store_id and to_store_id must be different', 1;
        IF @ProductId IS NULL OR NOT EXISTS
            (SELECT 1 FROM dbo.products WHERE product_id = @ProductId)
            THROW 50005, N'product_id does not exist', 1;
        IF @Quantity IS NULL OR @Quantity <= 0
            THROW 50005, N'quantity must be greater than 0', 1;
        IF @Priority IS NULL OR @Priority NOT IN ('low', 'normal', 'high', 'urgent')
            THROW 50005, N'priority is not valid', 1;

        DECLARE @Available DECIMAL(15,3);
        SELECT @Available = ISNULL(SUM(quantity), 0)
        FROM dbo.inventory
        WHERE store_id = @FromStoreId
          AND product_id = @ProductId
          AND (@ExpiryDate IS NULL OR expiry_date = @ExpiryDate);

        IF @Available < @Quantity
            THROW 50004, N'The source store does not have enough stock for this transfer', 1;

        DECLARE @TempCode NVARCHAR(30) = N'TMP-' + CONVERT(NVARCHAR(36), NEWID());

        INSERT INTO dbo.transfer_requests
            (transfer_code, from_store_id, to_store_id, product_id, quantity,
             expiry_date, status, priority, reason, note, requested_by)
        VALUES
            (@TempCode, @FromStoreId, @ToStoreId, @ProductId, @Quantity,
             @ExpiryDate, 'proposed', @Priority, @Reason, @Note, @RequestedBy);

        DECLARE @NewId INT = CAST(SCOPE_IDENTITY() AS INT);
        DECLARE @FinalCode NVARCHAR(30) =
            N'TR' + RIGHT(N'000000' + CONVERT(NVARCHAR(10), @NewId), 6);

        UPDATE dbo.transfer_requests
        SET transfer_code = @FinalCode, updated_at = SYSDATETIME()
        WHERE transfer_id = @NewId;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
        EXEC dbo.sp_Transfer_Get @TransferId = @NewId;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        IF ERROR_NUMBER() IN (2601, 2627)
            THROW 50002, N'A transfer with this code already exists', 1;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Transfer_Submit
    @TransferId INT,
    @UserId     INT = NULL
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        DECLARE @Status VARCHAR(20);
        SELECT @Status = status FROM dbo.transfer_requests WHERE transfer_id = @TransferId;
        IF @Status IS NULL THROW 50001, N'Transfer request not found', 1;
        IF @Status <> 'proposed'
            THROW 50004, N'Only a proposed transfer can be submitted for approval', 1;

        UPDATE dbo.transfer_requests
        SET status = 'pending',
            requested_by = COALESCE(requested_by, @UserId),
            updated_at = SYSDATETIME()
        WHERE transfer_id = @TransferId;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
        EXEC dbo.sp_Transfer_Get @TransferId = @TransferId;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Transfer_Approve
    @TransferId INT,
    @ApprovedBy INT = NULL,
    @Note       NVARCHAR(MAX) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        DECLARE @Status VARCHAR(20);
        SELECT @Status = status FROM dbo.transfer_requests WHERE transfer_id = @TransferId;
        IF @Status IS NULL THROW 50001, N'Transfer request not found', 1;
        IF @Status NOT IN ('proposed', 'pending')
            THROW 50004, N'Only a proposed or pending transfer can be approved', 1;

        UPDATE dbo.transfer_requests
        SET status = 'approved',
            approved_by = @ApprovedBy,
            approved_at = SYSDATETIME(),
            note = COALESCE(@Note, note),
            updated_at = SYSDATETIME()
        WHERE transfer_id = @TransferId;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
        EXEC dbo.sp_Transfer_Get @TransferId = @TransferId;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Transfer_Reject
    @TransferId INT,
    @RejectedBy INT = NULL,
    @Reason     NVARCHAR(MAX) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        DECLARE @Status VARCHAR(20);
        SELECT @Status = status FROM dbo.transfer_requests WHERE transfer_id = @TransferId;
        IF @Status IS NULL THROW 50001, N'Transfer request not found', 1;
        IF @Status NOT IN ('proposed', 'pending')
            THROW 50004, N'Only a proposed or pending transfer can be rejected', 1;

        UPDATE dbo.transfer_requests
        SET status = 'rejected',
            rejected_by = @RejectedBy,
            rejected_at = SYSDATETIME(),
            note = COALESCE(@Reason, note),
            updated_at = SYSDATETIME()
        WHERE transfer_id = @TransferId;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
        EXEC dbo.sp_Transfer_Get @TransferId = @TransferId;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Transfer_Cancel
    @TransferId INT,
    @UserId     INT = NULL
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        DECLARE @Status VARCHAR(20);
        SELECT @Status = status FROM dbo.transfer_requests WHERE transfer_id = @TransferId;
        IF @Status IS NULL THROW 50001, N'Transfer request not found', 1;
        IF @Status NOT IN ('proposed', 'pending')
            THROW 50004, N'Only a proposed or pending transfer can be cancelled', 1;

        UPDATE dbo.transfer_requests
        SET status = 'cancelled',
            note = COALESCE(note, N'Cancelled by user'),
            updated_at = SYSDATETIME()
        WHERE transfer_id = @TransferId;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
        EXEC dbo.sp_Transfer_Get @TransferId = @TransferId;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Transfer_Ship
    @TransferId INT,
    @ShippedBy  INT = NULL
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        DECLARE @Status VARCHAR(20);
        SELECT @Status = status FROM dbo.transfer_requests WHERE transfer_id = @TransferId;
        IF @Status IS NULL THROW 50001, N'Transfer request not found', 1;
        IF @Status <> 'approved'
            THROW 50004, N'Only an approved transfer can be shipped', 1;

        UPDATE dbo.transfer_requests
        SET status = 'in_transit',
            shipped_by = @ShippedBy,
            shipped_at = SYSDATETIME(),
            updated_at = SYSDATETIME()
        WHERE transfer_id = @TransferId;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
        EXEC dbo.sp_Transfer_Get @TransferId = @TransferId;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Transfer_Complete
    @TransferId INT,
    @UserId     INT = NULL
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        DECLARE @FromStoreId INT, @ToStoreId INT, @ProductId INT,
                @Qty DECIMAL(15,3), @ExpiryDate DATE, @Status VARCHAR(20);

        SELECT @FromStoreId = from_store_id,
               @ToStoreId = to_store_id,
               @ProductId = product_id,
               @Qty = quantity,
               @ExpiryDate = expiry_date,
               @Status = status
        FROM dbo.transfer_requests
        WHERE transfer_id = @TransferId;

        IF @FromStoreId IS NULL THROW 50001, N'Transfer request not found', 1;
        IF @Status <> 'in_transit'
            THROW 50004, N'Only a transfer in transit can be completed', 1;

        /* ---- 1. Deduct from the source store (FEFO when no expiry given) ---- */
        DECLARE @Remaining DECIMAL(15,3) = @Qty;
        DECLARE @BatchId BIGINT, @BatchQty DECIMAL(15,3), @BatchExpiry DATE,
                @Take DECIMAL(15,3);

        IF @ExpiryDate IS NOT NULL
        BEGIN
            SELECT @BatchId = inventory_id, @BatchQty = quantity
            FROM dbo.inventory
            WHERE store_id = @FromStoreId
              AND product_id = @ProductId
              AND expiry_date = @ExpiryDate;

            IF @BatchId IS NULL
                THROW 50004, N'The source batch for this transfer no longer exists', 1;
            IF @BatchQty < @Qty
                THROW 50004, N'The source batch does not have enough quantity', 1;

            UPDATE dbo.inventory
            SET quantity = quantity - @Qty, updated_at = SYSDATETIME()
            WHERE inventory_id = @BatchId;

            INSERT INTO dbo.inventory_transactions
                (store_id, product_id, expiry_date, transaction_type, quantity,
                 unit_cost, reference_type, reference_id, user_id, note)
            VALUES
                (@FromStoreId, @ProductId, @ExpiryDate, 'export', @Qty,
                 NULL, 'transfer', @TransferId, @UserId, N'Stock transferred out');

            SET @Remaining = 0;
        END
        ELSE
        BEGIN
            WHILE @Remaining > 0
            BEGIN
                SET @BatchId = NULL;
                SELECT TOP 1
                    @BatchId = inventory_id,
                    @BatchQty = quantity,
                    @BatchExpiry = expiry_date
                FROM dbo.inventory
                WHERE store_id = @FromStoreId
                  AND product_id = @ProductId
                  AND quantity > 0
                ORDER BY CASE WHEN expiry_date IS NULL THEN 1 ELSE 0 END,
                         expiry_date,
                         inventory_id;

                IF @BatchId IS NULL BREAK;

                SET @Take = CASE WHEN @BatchQty < @Remaining THEN @BatchQty ELSE @Remaining END;

                UPDATE dbo.inventory
                SET quantity = quantity - @Take, updated_at = SYSDATETIME()
                WHERE inventory_id = @BatchId;

                INSERT INTO dbo.inventory_transactions
                    (store_id, product_id, expiry_date, transaction_type, quantity,
                     unit_cost, reference_type, reference_id, user_id, note)
                VALUES
                    (@FromStoreId, @ProductId, @BatchExpiry, 'export', @Take,
                     NULL, 'transfer', @TransferId, @UserId, N'Stock transferred out');

                SET @Remaining = @Remaining - @Take;
            END

            IF @Remaining > 0
                THROW 50004, N'The source store does not have enough stock any more', 1;
        END

        /* ---- 2. Add to the destination store (merge into an existing batch) ---- */
        DECLARE @DestBatchId BIGINT = NULL;

        IF @ExpiryDate IS NOT NULL
        BEGIN
            SELECT TOP 1 @DestBatchId = inventory_id
            FROM dbo.inventory
            WHERE store_id = @ToStoreId
              AND product_id = @ProductId
              AND expiry_date = @ExpiryDate;
        END
        ELSE
        BEGIN
            SELECT TOP 1 @DestBatchId = inventory_id
            FROM dbo.inventory
            WHERE store_id = @ToStoreId
              AND product_id = @ProductId
              AND expiry_date IS NULL;
        END

        IF @DestBatchId IS NOT NULL
        BEGIN
            UPDATE dbo.inventory
            SET quantity = quantity + @Qty, updated_at = SYSDATETIME()
            WHERE inventory_id = @DestBatchId;
        END
        ELSE
        BEGIN
            INSERT INTO dbo.inventory
                (store_id, product_id, expiry_date, quantity, received_date, batch_code)
            VALUES
                (@ToStoreId, @ProductId, @ExpiryDate, @Qty,
                 CAST(SYSDATETIME() AS DATE), N'TRANSFER');
        END

        INSERT INTO dbo.inventory_transactions
            (store_id, product_id, expiry_date, transaction_type, quantity,
             unit_cost, reference_type, reference_id, user_id, note)
        VALUES
            (@ToStoreId, @ProductId, @ExpiryDate, 'import', @Qty,
             NULL, 'transfer', @TransferId, @UserId, N'Stock transferred in');

        /* ---- 3. Close the request ---- */
        UPDATE dbo.transfer_requests
        SET status = 'received',
            received_by = @UserId,
            completed_at = SYSDATETIME(),
            updated_at = SYSDATETIME()
        WHERE transfer_id = @TransferId;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
        EXEC dbo.sp_Transfer_Get @TransferId = @TransferId;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

/* --- 4b. Dem so yeu cau theo trang thai (cho thanh quy trinh tren UI) --- */

CREATE OR ALTER PROCEDURE dbo.sp_Transfer_Summary
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        SELECT status, COUNT(*) AS total
        FROM dbo.transfer_requests
        GROUP BY status;

        SELECT COUNT(*) AS total,
               ISNULL(SUM(quantity), 0) AS total_quantity,
               ISNULL(SUM(CASE WHEN status = 'in_transit' THEN quantity ELSE 0 END), 0) AS in_transit_quantity
        FROM dbo.transfer_requests;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

/* -------------------------------------------------------------------------
   5. Seasonal forecast

   Tinh chi so mua vu cho tung san pham tu du lieu ban hang lich su.

   LUU Y PHUONG PHAP: chi so o day la chi so TUONG DOI, khong phai chi so
   tuyet doi. Neu lay (doanh so TB/ngay trong mua) chia cho (doanh so TB/ngay
   ca nam) thi moi san pham deu ra cung mot kieu: thang 7 cao, thang 1 thap
   (xem AGENTS.md - mua vu Walmart tac dong dong deu len 50 san pham). Khi do
   khong san pham nao "noi bat" trong mua nao va ca bang deu la mot gia tri.

   Vi vay chi so duoc chuan hoa 2 lan:

       product_share = doanh so cua san pham trong mua / doanh so ca nam cua no
       market_share  = doanh so cua CA HE THONG trong mua / tong doanh so
       seasonal_index = product_share / market_share

   Nho vay phan mua vu chung bi triet tieu, con lai la muc do "san pham nay
   tang/giam trong mua nay manh hon hay yeu hon muc chung".

   VI SAO KHONG DUNG NGUONG CO DINH 1.05 / 0.95:
   Bien do chi so tinh duoc chi khoang 0.992 - 1.009 (da do). Mua vu trong
   dataset Walmart gan nhu tac dong deu len ca 50 san pham, nen khong san pham
   nao vuot 1.05. Neu dung nguong co dinh thi ca bang deu 'neutral' - vo dung.

   Vi vay khuyen nghi dua tren XEP HANG trong tung mua:
       top 20% chi so cao nhat  -> 'import'
       bottom 20% chi so thap nhat -> 'avoid'
       con lai                   -> 'neutral'
   Voi 50 san pham: 10 import + 10 avoid + 30 neutral moi mua. Cach nay luon
   cho ra danh sach hanh dong duoc, va van trung thuc vi no noi ro la so sanh
   TUONG DOI giua cac san pham, khong phai mot nguong tuyet doi.

   Mua chia theo thang:
       spring = 2,3,4   summer = 5,6,7   autumn = 8,9,10   winter = 11,12,1
   ------------------------------------------------------------------------- */

CREATE OR ALTER PROCEDURE dbo.sp_Forecasts_Seasonal
    @Season VARCHAR(10) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        IF OBJECT_ID(N'tempdb..#tagged') IS NOT NULL DROP TABLE #tagged;

        CREATE TABLE #tagged (
            product_id  INT           NOT NULL,
            sale_date   DATE          NOT NULL,
            qty         DECIMAL(18,3) NOT NULL,
            season_code VARCHAR(10)   NOT NULL
        );

        INSERT INTO #tagged (product_id, sale_date, qty, season_code)
        SELECT
            oi.product_id,
            CAST(o.order_date AS DATE) AS sale_date,
            SUM(oi.quantity) AS qty,
            CASE
                WHEN MONTH(o.order_date) IN (2, 3, 4) THEN 'spring'
                WHEN MONTH(o.order_date) IN (5, 6, 7) THEN 'summer'
                WHEN MONTH(o.order_date) IN (8, 9, 10) THEN 'autumn'
                ELSE 'winter'
            END AS season_code
        FROM dbo.order_items oi
        JOIN dbo.orders o ON o.order_id = oi.order_id
        WHERE o.status = 'completed'
          AND o.order_type = 'sale'
        GROUP BY
            oi.product_id,
            CAST(o.order_date AS DATE),
            CASE
                WHEN MONTH(o.order_date) IN (2, 3, 4) THEN 'spring'
                WHEN MONTH(o.order_date) IN (5, 6, 7) THEN 'summer'
                WHEN MONTH(o.order_date) IN (8, 9, 10) THEN 'autumn'
                ELSE 'winter'
            END;

        IF NOT EXISTS (SELECT 1 FROM #tagged)
        BEGIN
            IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
            RETURN;
        END

        SELECT season_code, COUNT(DISTINCT sale_date) AS days
        INTO #season_days
        FROM #tagged
        GROUP BY season_code;

        SELECT COUNT(DISTINCT sale_date) AS days,
               MIN(sale_date) AS date_from,
               MAX(sale_date) AS date_to
        INTO #overall
        FROM #tagged;

        SELECT product_id, SUM(qty) AS total_qty
        INTO #product_total
        FROM #tagged
        GROUP BY product_id;

        SELECT product_id, season_code, SUM(qty) AS total_qty
        INTO #product_season
        FROM #tagged
        GROUP BY product_id, season_code;

        SELECT season_code, SUM(qty) AS total_qty
        INTO #season_total
        FROM #tagged
        GROUP BY season_code;

        SELECT SUM(qty) AS total_qty
        INTO #grand_total
        FROM #tagged;

        SELECT
            x.product_id,
            x.product_code,
            x.product_name,
            x.unit,
            x.category_name,
            x.season_code,
            x.season_order,
            x.avg_daily_qty,
            x.overall_daily_qty,
            x.sample_days,
            x.season_share,
            x.seasonal_index,
            x.rank_in_season,
            x.season_products,
            CASE
                WHEN x.rank_in_season <= x.import_cut THEN 'import'
                WHEN x.rank_in_season > x.season_products - x.import_cut THEN 'avoid'
                ELSE 'neutral'
            END AS recommendation,
            x.data_from,
            x.data_to
        FROM (
            SELECT
                ps.product_id,
                p.product_code,
                p.product_name,
                p.unit,
                cat.category_name,
                ps.season_code,
                CASE ps.season_code
                    WHEN 'spring' THEN 1
                    WHEN 'summer' THEN 2
                    WHEN 'autumn' THEN 3
                    ELSE 4
                END AS season_order,
                CAST(ps.total_qty / NULLIF(sd.days, 0) AS DECIMAL(18,3)) AS avg_daily_qty,
                CAST(pt.total_qty / NULLIF(o.days, 0) AS DECIMAL(18,3)) AS overall_daily_qty,
                sd.days AS sample_days,
                CAST(ps.total_qty / NULLIF(pt.total_qty, 0) AS DECIMAL(12,6)) AS season_share,
                CAST(
                    (ps.total_qty / NULLIF(pt.total_qty, 0))
                    / NULLIF(st.total_qty / NULLIF(g.total_qty, 0), 0)
                    AS DECIMAL(10,4)
                ) AS seasonal_index,
                ROW_NUMBER() OVER (
                    PARTITION BY ps.season_code
                    ORDER BY
                        (ps.total_qty / NULLIF(pt.total_qty, 0))
                        / NULLIF(st.total_qty / NULLIF(g.total_qty, 0), 0) DESC,
                        p.product_name
                ) AS rank_in_season,
                COUNT(*) OVER (PARTITION BY ps.season_code) AS season_products,
                CAST(CEILING(COUNT(*) OVER (PARTITION BY ps.season_code) * 0.2) AS INT)
                    AS import_cut,
                CONVERT(VARCHAR(10), o.date_from, 23) AS data_from,
                CONVERT(VARCHAR(10), o.date_to, 23) AS data_to
            FROM #product_season ps
            JOIN #season_days sd ON sd.season_code = ps.season_code
            JOIN #product_total pt ON pt.product_id = ps.product_id
            JOIN #season_total st ON st.season_code = ps.season_code
            CROSS JOIN #grand_total g
            CROSS JOIN #overall o
            JOIN dbo.products p ON p.product_id = ps.product_id
            JOIN dbo.categories cat ON cat.category_id = p.category_id
        ) x
        WHERE (@Season IS NULL OR x.season_code = @Season)
        ORDER BY x.season_order, x.seasonal_index DESC, x.product_name;

        DROP TABLE #tagged;
        DROP TABLE #season_days;
        DROP TABLE #overall;
        DROP TABLE #product_total;
        DROP TABLE #product_season;
        DROP TABLE #season_total;
        DROP TABLE #grand_total;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

PRINT N'011-transfers-seasonal.sql applied.';
GO
