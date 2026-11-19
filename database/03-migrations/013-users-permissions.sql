SET QUOTED_IDENTIFIER ON;
SET ANSI_NULLS ON;
GO

/* =========================================================================
   013 - USER MANAGEMENT + DETAILED PERMISSIONS (19/11/2026)

   Adds per-user permission flags and an avatar reference to `users`, then
   rebuilds the auth read procedures so `/api/v1/auth/me` can return the new
   fields, and adds the CRUD procedures used by `user_router.py`.

   Design notes
   ------------
   * Columns are added with ALTER TABLE. Existing rows keep every value and
     the table is never dropped.
   * The backfill only runs on the first execution (detected by the absence
     of `can_manage_user`), so re-running the file never overwrites an
     administrator's choices.
   * `uq_users_email` is a UNIQUE constraint, and SQL Server treats multiple
     NULLs as duplicates. It is replaced by a filtered unique index so an
     account without an email can coexist with other accounts without one.
     This is the same pattern already used by `inventory`.
   * The owner display name is written with NCHAR(224) so this file stays
     pure ASCII (project rule) while still producing "Toan" with a diacritic.
   * Business error codes follow the project contract:
       50001 NOT_FOUND | 50002 DUPLICATE | 50003 REFERENCED
       50004 INVALID_STATE | 50005 INVALID_INPUT
   ========================================================================= */

/* The flag travels across GO through a temp table: local variables do not
   survive a batch boundary, and the backfill UPDATE cannot be compiled in
   the same batch as the ALTER TABLE that creates the columns. */
CREATE TABLE #users_permissions_flags (fresh BIT NOT NULL);
INSERT INTO #users_permissions_flags (fresh)
VALUES (CASE WHEN COL_LENGTH('dbo.users', 'can_manage_user') IS NULL THEN 1 ELSE 0 END);

IF COL_LENGTH('dbo.users', 'avatar_url') IS NULL
    ALTER TABLE dbo.users ADD avatar_url NVARCHAR(500) NULL;

IF COL_LENGTH('dbo.users', 'can_edit_product') IS NULL
    ALTER TABLE dbo.users ADD can_edit_product BIT NOT NULL
        CONSTRAINT df_users_can_edit_product DEFAULT (0);

IF COL_LENGTH('dbo.users', 'can_delete_product') IS NULL
    ALTER TABLE dbo.users ADD can_delete_product BIT NOT NULL
        CONSTRAINT df_users_can_delete_product DEFAULT (0);

IF COL_LENGTH('dbo.users', 'can_view_report') IS NULL
    ALTER TABLE dbo.users ADD can_view_report BIT NOT NULL
        CONSTRAINT df_users_can_view_report DEFAULT (0);

IF COL_LENGTH('dbo.users', 'can_manage_inventory') IS NULL
    ALTER TABLE dbo.users ADD can_manage_inventory BIT NOT NULL
        CONSTRAINT df_users_can_manage_inventory DEFAULT (0);

IF COL_LENGTH('dbo.users', 'can_manage_order') IS NULL
    ALTER TABLE dbo.users ADD can_manage_order BIT NOT NULL
        CONSTRAINT df_users_can_manage_order DEFAULT (0);

IF COL_LENGTH('dbo.users', 'can_manage_transfer') IS NULL
    ALTER TABLE dbo.users ADD can_manage_transfer BIT NOT NULL
        CONSTRAINT df_users_can_manage_transfer DEFAULT (0);

IF COL_LENGTH('dbo.users', 'can_manage_user') IS NULL
    ALTER TABLE dbo.users ADD can_manage_user BIT NOT NULL
        CONSTRAINT df_users_can_manage_user DEFAULT (0);
GO

IF (SELECT fresh FROM #users_permissions_flags) = 1
BEGIN
    /* Sensible starting point: the owner can do everything, a manager has
       the operational rights but cannot delete master data or manage users,
       and staff only work with inventory, orders and transfers. */
    UPDATE dbo.users
    SET can_edit_product     = CASE WHEN role IN ('owner', 'manager') THEN 1 ELSE 0 END,
        can_delete_product   = CASE WHEN role = 'owner' THEN 1 ELSE 0 END,
        can_view_report      = CASE WHEN role IN ('owner', 'manager') THEN 1 ELSE 0 END,
        can_manage_inventory = 1,
        can_manage_order     = 1,
        can_manage_transfer  = 1,
        can_manage_user      = CASE WHEN role = 'owner' THEN 1 ELSE 0 END;

    /* Demo administrator: display name "Toan" (with diacritic) and the
       bundled avatar key used by the React header. */
    UPDATE dbo.users
    SET full_name = N'To' + NCHAR(224) + N'n',
        avatar_url = N'toan'
    WHERE username = N'owner';
END
GO

DROP TABLE #users_permissions_flags;
GO

/* -------------------------------------------------------------------------
   Let more than one account have no email address.
   ------------------------------------------------------------------------- */
IF EXISTS (
    SELECT 1 FROM sys.key_constraints
    WHERE name = 'uq_users_email'
      AND parent_object_id = OBJECT_ID('dbo.users')
)
BEGIN
    ALTER TABLE dbo.users DROP CONSTRAINT uq_users_email;
END
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'uq_users_email'
      AND object_id = OBJECT_ID('dbo.users')
)
BEGIN
    CREATE UNIQUE INDEX uq_users_email
        ON dbo.users (email)
        WHERE email IS NOT NULL;
END
GO


/* =========================================================================
   AUTH READ PROCEDURES - rebuilt to expose avatar + permissions
   ========================================================================= */

CREATE OR ALTER PROCEDURE dbo.sp_Users_GetByUsername
    @Username NVARCHAR(50)
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        SELECT user_id, username, email, password_hash, full_name, role,
               store_id, is_active, avatar_url,
               can_edit_product, can_delete_product, can_view_report,
               can_manage_inventory, can_manage_order, can_manage_transfer,
               can_manage_user, created_at, updated_at
        FROM dbo.users
        WHERE username = @Username;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

/* Returns password_hash as well: /auth/change-password compares the current
   password against it, and the previous definition omitted that column. */
CREATE OR ALTER PROCEDURE dbo.sp_Users_GetById
    @UserId INT
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;
        IF NOT EXISTS (SELECT 1 FROM dbo.users WHERE user_id = @UserId)
            THROW 50001, N'User not found', 1;

        SELECT user_id, username, email, password_hash, full_name, role,
               store_id, is_active, avatar_url,
               can_edit_product, can_delete_product, can_view_report,
               can_manage_inventory, can_manage_order, can_manage_transfer,
               can_manage_user, created_at, updated_at
        FROM dbo.users
        WHERE user_id = @UserId;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO


/* =========================================================================
   CRUD PROCEDURES
   ========================================================================= */

CREATE OR ALTER PROCEDURE dbo.sp_Users_List
    @Search   NVARCHAR(150) = NULL,
    @Role     VARCHAR(20)   = NULL,
    @IsActive BIT           = NULL,
    @Page     INT           = 1,
    @PageSize INT           = 20
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @Offset INT;

    IF @Page IS NULL OR @Page < 1 SET @Page = 1;
    IF @PageSize IS NULL OR @PageSize < 1 SET @PageSize = 20;
    IF @PageSize > 200 SET @PageSize = 200;
    IF @Role = '' SET @Role = NULL;
    IF @Search = '' SET @Search = NULL;
    SET @Offset = (@Page - 1) * @PageSize;

    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        SELECT COUNT(*) AS total
        FROM dbo.users u
        WHERE (@Search IS NULL
                OR u.username LIKE N'%' + @Search + N'%'
                OR u.full_name LIKE N'%' + @Search + N'%'
                OR ISNULL(u.email, N'') LIKE N'%' + @Search + N'%')
          AND (@Role IS NULL OR u.role = @Role)
          AND (@IsActive IS NULL OR u.is_active = @IsActive);

        SELECT u.user_id, u.username, u.email, u.full_name, u.role,
               u.store_id, s.store_name, u.is_active, u.avatar_url,
               u.can_edit_product, u.can_delete_product, u.can_view_report,
               u.can_manage_inventory, u.can_manage_order,
               u.can_manage_transfer, u.can_manage_user,
               u.created_at, u.updated_at
        FROM dbo.users u
        LEFT JOIN dbo.stores s ON s.store_id = u.store_id
        WHERE (@Search IS NULL
                OR u.username LIKE N'%' + @Search + N'%'
                OR u.full_name LIKE N'%' + @Search + N'%'
                OR ISNULL(u.email, N'') LIKE N'%' + @Search + N'%')
          AND (@Role IS NULL OR u.role = @Role)
          AND (@IsActive IS NULL OR u.is_active = @IsActive)
        ORDER BY u.user_id
        OFFSET @Offset ROWS FETCH NEXT @PageSize ROWS ONLY;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Users_Create
    @Username            NVARCHAR(50),
    @Email               NVARCHAR(150) = NULL,
    @PasswordHash        NVARCHAR(255),
    @FullName            NVARCHAR(150),
    @Role                VARCHAR(20)   = 'staff',
    @StoreId             INT           = NULL,
    @IsActive            BIT           = 1,
    @AvatarUrl           NVARCHAR(500) = NULL,
    @CanEditProduct      BIT           = 0,
    @CanDeleteProduct    BIT           = 0,
    @CanViewReport       BIT           = 0,
    @CanManageInventory  BIT           = 0,
    @CanManageOrder      BIT           = 0,
    @CanManageTransfer   BIT           = 0,
    @CanManageUser       BIT           = 0
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @NewUserId INT;

    SET @Username = LTRIM(RTRIM(@Username));
    SET @FullName = LTRIM(RTRIM(@FullName));
    SET @Email = NULLIF(LTRIM(RTRIM(ISNULL(@Email, N''))), N'');

    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        IF @Username IS NULL OR LEN(@Username) = 0
            THROW 50005, N'Username is required', 1;
        IF @FullName IS NULL OR LEN(@FullName) = 0
            THROW 50005, N'Full name is required', 1;
        IF @PasswordHash IS NULL OR LEN(@PasswordHash) < 20
            THROW 50005, N'A password hash is required', 1;
        IF @Role NOT IN ('owner', 'manager', 'staff')
            THROW 50005, N'Role must be owner, manager or staff', 1;

        IF EXISTS (SELECT 1 FROM dbo.users WHERE username = @Username)
            THROW 50002, N'Username already exists', 1;
        IF @Email IS NOT NULL
           AND EXISTS (SELECT 1 FROM dbo.users WHERE email = @Email)
            THROW 50002, N'Email already exists', 1;
        IF @StoreId IS NOT NULL
           AND NOT EXISTS (SELECT 1 FROM dbo.stores WHERE store_id = @StoreId)
            THROW 50005, N'Store does not exist', 1;

        INSERT INTO dbo.users (
            username, email, password_hash, full_name, role, store_id,
            is_active, avatar_url,
            can_edit_product, can_delete_product, can_view_report,
            can_manage_inventory, can_manage_order, can_manage_transfer,
            can_manage_user
        )
        VALUES (
            @Username, @Email, @PasswordHash, @FullName, @Role, @StoreId,
            ISNULL(@IsActive, 1), @AvatarUrl,
            ISNULL(@CanEditProduct, 0), ISNULL(@CanDeleteProduct, 0),
            ISNULL(@CanViewReport, 0), ISNULL(@CanManageInventory, 0),
            ISNULL(@CanManageOrder, 0), ISNULL(@CanManageTransfer, 0),
            ISNULL(@CanManageUser, 0)
        );

        SET @NewUserId = SCOPE_IDENTITY();

        SELECT u.user_id, u.username, u.email, u.full_name, u.role,
               u.store_id, s.store_name, u.is_active, u.avatar_url,
               u.can_edit_product, u.can_delete_product, u.can_view_report,
               u.can_manage_inventory, u.can_manage_order,
               u.can_manage_transfer, u.can_manage_user,
               u.created_at, u.updated_at
        FROM dbo.users u
        LEFT JOIN dbo.stores s ON s.store_id = u.store_id
        WHERE u.user_id = @NewUserId;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Users_Update
    @UserId              INT,
    @Username            NVARCHAR(50),
    @Email               NVARCHAR(150) = NULL,
    @PasswordHash        NVARCHAR(255) = NULL,
    @FullName            NVARCHAR(150),
    @Role                VARCHAR(20),
    @StoreId             INT           = NULL,
    @IsActive            BIT           = 1,
    @AvatarUrl           NVARCHAR(500) = NULL,
    @CanEditProduct      BIT           = 0,
    @CanDeleteProduct    BIT           = 0,
    @CanViewReport       BIT           = 0,
    @CanManageInventory  BIT           = 0,
    @CanManageOrder      BIT           = 0,
    @CanManageTransfer   BIT           = 0,
    @CanManageUser       BIT           = 0
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @CurrentRole VARCHAR(20);
    DECLARE @ActiveOwners INT;

    SET @Username = LTRIM(RTRIM(@Username));
    SET @FullName = LTRIM(RTRIM(@FullName));
    SET @Email = NULLIF(LTRIM(RTRIM(ISNULL(@Email, N''))), N'');
    SET @PasswordHash = NULLIF(@PasswordHash, N'');

    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        SELECT @CurrentRole = role FROM dbo.users WHERE user_id = @UserId;
        IF @CurrentRole IS NULL
            THROW 50001, N'User not found', 1;

        IF @Username IS NULL OR LEN(@Username) = 0
            THROW 50005, N'Username is required', 1;
        IF @FullName IS NULL OR LEN(@FullName) = 0
            THROW 50005, N'Full name is required', 1;
        IF @Role NOT IN ('owner', 'manager', 'staff')
            THROW 50005, N'Role must be owner, manager or staff', 1;

        IF EXISTS (SELECT 1 FROM dbo.users
                   WHERE username = @Username AND user_id <> @UserId)
            THROW 50002, N'Username already exists', 1;
        IF @Email IS NOT NULL
           AND EXISTS (SELECT 1 FROM dbo.users
                       WHERE email = @Email AND user_id <> @UserId)
            THROW 50002, N'Email already exists', 1;
        IF @StoreId IS NOT NULL
           AND NOT EXISTS (SELECT 1 FROM dbo.stores WHERE store_id = @StoreId)
            THROW 50005, N'Store does not exist', 1;

        /* Never leave the system without an active owner. */
        IF @CurrentRole = 'owner' AND (@Role <> 'owner' OR ISNULL(@IsActive, 1) = 0)
        BEGIN
            SELECT @ActiveOwners = COUNT(*)
            FROM dbo.users
            WHERE role = 'owner' AND is_active = 1;

            IF @ActiveOwners <= 1
                THROW 50004, N'Cannot demote or deactivate the last active owner', 1;
        END

        UPDATE dbo.users
        SET username            = @Username,
            email               = @Email,
            full_name           = @FullName,
            role                = @Role,
            store_id            = @StoreId,
            is_active           = ISNULL(@IsActive, 1),
            avatar_url          = @AvatarUrl,
            password_hash       = CASE WHEN @PasswordHash IS NULL
                                       THEN password_hash
                                       ELSE @PasswordHash END,
            can_edit_product    = ISNULL(@CanEditProduct, 0),
            can_delete_product  = ISNULL(@CanDeleteProduct, 0),
            can_view_report     = ISNULL(@CanViewReport, 0),
            can_manage_inventory = ISNULL(@CanManageInventory, 0),
            can_manage_order     = ISNULL(@CanManageOrder, 0),
            can_manage_transfer  = ISNULL(@CanManageTransfer, 0),
            can_manage_user      = ISNULL(@CanManageUser, 0)
        WHERE user_id = @UserId;

        SELECT u.user_id, u.username, u.email, u.full_name, u.role,
               u.store_id, s.store_name, u.is_active, u.avatar_url,
               u.can_edit_product, u.can_delete_product, u.can_view_report,
               u.can_manage_inventory, u.can_manage_order,
               u.can_manage_transfer, u.can_manage_user,
               u.created_at, u.updated_at
        FROM dbo.users u
        LEFT JOIN dbo.stores s ON s.store_id = u.store_id
        WHERE u.user_id = @UserId;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Users_Delete
    @UserId INT
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @CurrentRole VARCHAR(20);
    DECLARE @CurrentActive BIT;
    DECLARE @ActiveOwners INT;

    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        SELECT @CurrentRole = role, @CurrentActive = is_active
        FROM dbo.users WHERE user_id = @UserId;

        IF @CurrentRole IS NULL
            THROW 50001, N'User not found', 1;

        /* Keep at least one working owner account. */
        IF @CurrentRole = 'owner' AND @CurrentActive = 1
        BEGIN
            SELECT @ActiveOwners = COUNT(*)
            FROM dbo.users
            WHERE role = 'owner' AND is_active = 1;

            IF @ActiveOwners <= 1
                THROW 50004, N'Cannot delete the last active owner', 1;
        END

        IF EXISTS (
            SELECT 1 FROM dbo.transfer_requests
            WHERE requested_by = @UserId OR approved_by = @UserId
               OR rejected_by = @UserId OR shipped_by = @UserId
               OR received_by = @UserId
        )
            THROW 50003, N'User is referenced by transfer requests; deactivate the account instead', 1;

        DELETE FROM dbo.users WHERE user_id = @UserId;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

PRINT N'013-users-permissions.sql applied.';
GO
