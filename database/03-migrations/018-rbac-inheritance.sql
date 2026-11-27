/* =========================================================================
   018 - RBAC ROLE-BASED INHERITANCE (27/11/2026)

   Chay file nay SAU database/03-migrations/017-smart-transfer-urgency.sql.

   Noi dung:
     1. sp_Users_Create        : bo qua cac tham so quyen, tu gan bo mac dinh
                                 theo role (owner / manager / staff).
     2. sp_Users_UpdatePermissionsByRole : cap nhat quyen cua MOT nguoi roi
                                 lan truyen (propagate) sang moi tai khoan
                                 DANG HOAT DONG cung vai tro.
     3. Chuan hoa du lieu cu   : dong bo 7 cot quyen theo vai tro (chi lan
                                 dau chay file).

   Rang buoc:
     * KHONG doi cau truc bang `users` (van giu role + 7 cot BIT).
     * Chi lan truyen cho `manager` va `staff`. Vai tro `owner` la tang tin
       cay cao nhat: hai owner khong duoc phep ghi de quyen cua nhau, neu
       khong mot owner co the tu khoa minh khoi he thong.
     * Chi lan truyen sang tai khoan co is_active = 1. Tai khoan da bi khoa
       giu nguyen quyen cu va se duoc dong bo khi mo khoa lai (lan luu ke
       tiep cua vai tro do).

   File giu ASCII (comment tieng Anh) de chay duoc tren Windows PowerShell.

   Chay: sqlcmd -S "LAPTOP-I39E3UT2\SQLEXPRESS" -U sa -P <mat_khau> -C ^
                 -d spoilage_predictor -I -b ^
                 -i database\03-migrations\018-rbac-inheritance.sql
   ========================================================================= */

SET QUOTED_IDENTIFIER ON;
SET ANSI_NULLS ON;
GO

/* The flag travels across GO through a temp table: local variables do not
   survive a batch boundary. It is 1 only on the first execution, so the
   one-time normalisation below never overwrites an administrator's choices
   when the file is re-run. */
CREATE TABLE #rbac_inheritance_flags (fresh BIT NOT NULL);
INSERT INTO #rbac_inheritance_flags (fresh)
VALUES (CASE WHEN OBJECT_ID('dbo.sp_Users_UpdatePermissionsByRole') IS NULL
             THEN 1 ELSE 0 END);
GO

/* -------------------------------------------------------------------------
   1. sp_Users_Create - the role owns the permission set

   The seven permission parameters are kept so existing callers keep working,
   but they are IGNORED: a new account always starts from its role's set.

   "Role's set" = what the ACTIVE members of that role currently use. Reading
   the peers (instead of always writing the factory defaults) is what keeps
   inheritance honest: if an administrator granted can_view_report to staff
   yesterday, a staff account created today must have it too, otherwise the
   same role would carry two different permission sets.

   Factory defaults (must match ROLE_DEFAULTS in UsersPage.jsx) are only used
   when the role has no active member yet:
     owner   : all seven flags on
     manager : all except can_delete_product and can_manage_user
     staff   : can_manage_inventory / order / transfer only
   ------------------------------------------------------------------------- */

CREATE OR ALTER PROCEDURE dbo.sp_Users_Create
    @Username            NVARCHAR(50),
    @Email               NVARCHAR(150) = NULL,
    @PasswordHash        NVARCHAR(255),
    @FullName            NVARCHAR(150),
    @Role                VARCHAR(20)   = 'staff',
    @StoreId             INT           = NULL,
    @IsActive            BIT           = 1,
    @AvatarUrl           NVARCHAR(500) = NULL,
    -- Accepted for backward compatibility, intentionally ignored.
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
    DECLARE @DefEditProduct    BIT;
    DECLARE @DefDeleteProduct  BIT;
    DECLARE @DefViewReport     BIT;
    DECLARE @DefManageInventory BIT;
    DECLARE @DefManageOrder    BIT;
    DECLARE @DefManageTransfer BIT;
    DECLARE @DefManageUser     BIT;

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

        /* Inherit the role's current set when it already has an active member. */
        IF EXISTS (SELECT 1 FROM dbo.users WHERE role = @Role AND is_active = 1)
        BEGIN
            SELECT TOP (1)
                   @DefEditProduct     = can_edit_product,
                   @DefDeleteProduct   = can_delete_product,
                   @DefViewReport      = can_view_report,
                   @DefManageInventory = can_manage_inventory,
                   @DefManageOrder     = can_manage_order,
                   @DefManageTransfer  = can_manage_transfer,
                   @DefManageUser      = can_manage_user
            FROM dbo.users
            WHERE role = @Role AND is_active = 1
            ORDER BY user_id;
        END
        ELSE IF @Role = 'owner'
        BEGIN
            SET @DefEditProduct = 1; SET @DefDeleteProduct = 1;
            SET @DefViewReport = 1; SET @DefManageInventory = 1;
            SET @DefManageOrder = 1; SET @DefManageTransfer = 1;
            SET @DefManageUser = 1;
        END
        ELSE IF @Role = 'manager'
        BEGIN
            SET @DefEditProduct = 1; SET @DefDeleteProduct = 0;
            SET @DefViewReport = 1; SET @DefManageInventory = 1;
            SET @DefManageOrder = 1; SET @DefManageTransfer = 1;
            SET @DefManageUser = 0;
        END
        ELSE
        BEGIN
            SET @DefEditProduct = 0; SET @DefDeleteProduct = 0;
            SET @DefViewReport = 0; SET @DefManageInventory = 1;
            SET @DefManageOrder = 1; SET @DefManageTransfer = 1;
            SET @DefManageUser = 0;
        END

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
            @DefEditProduct, @DefDeleteProduct, @DefViewReport,
            @DefManageInventory, @DefManageOrder, @DefManageTransfer,
            @DefManageUser
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

/* -------------------------------------------------------------------------
   2. sp_Users_UpdatePermissionsByRole - write once, apply to the role

   Result set 1: the updated target row (same shape as sp_Users_Update).
   Result set 2: { affected_users, affected_role } so the API can report how
                 many accounts the change touched.

   `affected_users` counts every account whose flags now equal the requested
   set: the active members of the role plus the target itself when it is
   locked (a locked account is still written, it just does not receive the
   propagation of its peers).
   ------------------------------------------------------------------------- */

CREATE OR ALTER PROCEDURE dbo.sp_Users_UpdatePermissionsByRole
    @UserId              INT,
    @Role                VARCHAR(20) = NULL,
    @CanEditProduct      BIT = 0,
    @CanDeleteProduct    BIT = 0,
    @CanViewReport       BIT = 0,
    @CanManageInventory  BIT = 0,
    @CanManageOrder      BIT = 0,
    @CanManageTransfer   BIT = 0,
    @CanManageUser       BIT = 0
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @CurrentRole   VARCHAR(20);
    DECLARE @EffectiveRole VARCHAR(20);
    DECLARE @AffectedUsers INT;
    DECLARE @ActiveOwners  INT;

    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        SELECT @CurrentRole = role FROM dbo.users WHERE user_id = @UserId;
        IF @CurrentRole IS NULL
            THROW 50001, N'User not found', 1;

        SET @Role = NULLIF(LTRIM(RTRIM(ISNULL(@Role, ''))), '');
        SET @EffectiveRole = ISNULL(@Role, @CurrentRole);
        IF @EffectiveRole NOT IN ('owner', 'manager', 'staff')
            THROW 50005, N'Role must be owner, manager or staff', 1;

        /* Demoting an owner still has to leave one active owner behind. */
        IF @CurrentRole = 'owner' AND @EffectiveRole <> 'owner'
        BEGIN
            SELECT @ActiveOwners = COUNT(*)
            FROM dbo.users
            WHERE role = 'owner' AND is_active = 1;

            IF @ActiveOwners <= 1
                THROW 50004, N'Cannot demote the last active owner', 1;
        END

        /* The target row always receives exactly the requested values. */
        UPDATE dbo.users
        SET role                 = @EffectiveRole,
            can_edit_product     = ISNULL(@CanEditProduct, 0),
            can_delete_product   = ISNULL(@CanDeleteProduct, 0),
            can_view_report      = ISNULL(@CanViewReport, 0),
            can_manage_inventory = ISNULL(@CanManageInventory, 0),
            can_manage_order     = ISNULL(@CanManageOrder, 0),
            can_manage_transfer  = ISNULL(@CanManageTransfer, 0),
            can_manage_user      = ISNULL(@CanManageUser, 0)
        WHERE user_id = @UserId;

        /* Role inheritance: every ACTIVE peer with the same role. Owner is
           excluded on purpose - see the header note. */
        IF @EffectiveRole IN ('manager', 'staff')
        BEGIN
            UPDATE dbo.users
            SET can_edit_product     = ISNULL(@CanEditProduct, 0),
                can_delete_product   = ISNULL(@CanDeleteProduct, 0),
                can_view_report      = ISNULL(@CanViewReport, 0),
                can_manage_inventory = ISNULL(@CanManageInventory, 0),
                can_manage_order     = ISNULL(@CanManageOrder, 0),
                can_manage_transfer  = ISNULL(@CanManageTransfer, 0),
                can_manage_user      = ISNULL(@CanManageUser, 0)
            WHERE role = @EffectiveRole
              AND is_active = 1
              AND user_id <> @UserId;

            SELECT @AffectedUsers = COUNT(*)
            FROM dbo.users
            WHERE role = @EffectiveRole
              AND (is_active = 1 OR user_id = @UserId);
        END
        ELSE
        BEGIN
            /* Owner: the change applies to this account only. */
            SET @AffectedUsers = 1;
        END

        SELECT u.user_id, u.username, u.email, u.full_name, u.role,
               u.store_id, s.store_name, u.is_active, u.avatar_url,
               u.can_edit_product, u.can_delete_product, u.can_view_report,
               u.can_manage_inventory, u.can_manage_order,
               u.can_manage_transfer, u.can_manage_user,
               u.created_at, u.updated_at
        FROM dbo.users u
        LEFT JOIN dbo.stores s ON s.store_id = u.store_id
        WHERE u.user_id = @UserId;

        SELECT @AffectedUsers AS affected_users,
               @EffectiveRole AS affected_role;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

/* -------------------------------------------------------------------------
   3. One-time normalisation of existing rows

   Until now every account could carry its own flag set. With inheritance the
   role owns the flags, so rows of the same role must agree. Runs only on the
   first execution of this file.
   ------------------------------------------------------------------------- */

IF (SELECT fresh FROM #rbac_inheritance_flags) = 1
BEGIN
    UPDATE dbo.users
    SET can_edit_product     = CASE WHEN role IN ('owner', 'manager') THEN 1 ELSE 0 END,
        can_delete_product   = CASE WHEN role = 'owner' THEN 1 ELSE 0 END,
        can_view_report      = CASE WHEN role IN ('owner', 'manager') THEN 1 ELSE 0 END,
        can_manage_inventory = 1,
        can_manage_order     = 1,
        can_manage_transfer  = 1,
        can_manage_user      = CASE WHEN role = 'owner' THEN 1 ELSE 0 END;
END
GO

DROP TABLE #rbac_inheritance_flags;
GO

PRINT N'018-rbac-inheritance.sql applied.';
GO
