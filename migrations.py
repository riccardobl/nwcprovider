# the migration file is where you build your database tables
# If you create a new release for your extension , remeember the migration file is like a blockchain, never edit only add!


async def m001_initial(db):
    """
    Initial templates table.
    """
    await db.execute(
        """
        CREATE TABLE nwc_service.maintable (
            id TEXT PRIMARY KEY,
            wallet TEXT NOT NULL,
            name TEXT NOT NULL,
            total INTEGER DEFAULT 0,
            lnurlpayamount INTEGER DEFAULT 0,
            lnurlwithdrawamount INTEGER DEFAULT 0,
            lnurlwithdraw TEXT,
            lnurlpay TEXT
        );
    """
    )


# Here we add another field to the database


async def m002_addtip_wallet(db):
    """
    Add total to templates table
    """
    await db.execute(
        """
        ALTER TABLE nwc_service.maintable ADD ticker INTEGER DEFAULT 1;
    """
    )
