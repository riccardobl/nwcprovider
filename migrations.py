import secp256k1

async def m001_initial(db):
    """
    Initial tables
    """
    await db.execute(
        """
        CREATE TABLE nwcprovider.keys (
            pubkey TEXT PRIMARY KEY,
            wallet TEXT NOT NULL, 
            description TEXT NOT NULL,
            expires_at INTEGER NOT NULL, 
            permissions TEXT NOT NULL,
            created_at INTEGER NOT NULL 
        );
        """
    )

    await db.execute(
        """
        CREATE TABLE nwcprovider.spent (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            pubkey TEXT NOT NULL, 
            amount_msats INTEGER NOT NULL,
            created_at INTEGER NOT NULL, 
            FOREIGN KEY(pubkey)  REFERENCES keys(pubkey) ON DELETE CASCADE
        );
        """
    )
 
    await db.execute(
          """
        CREATE TABLE nwcprovider.logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            pubkey TEXT NOT NULL,  
            payload TEXT NOT NULL,
            created_at INTEGER NOT NULL, 
            FOREIGN KEY(pubkey)  REFERENCES keys(pubkey) ON DELETE CASCADE
        );
        """
    )

    await db.execute(
        """
        CREATE TABLE nwcprovider.budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pubkey TEXT NOT NULL,
            budget_msats INTEGER NOT NULL,
            refresh_window INTEGER NOT NULL,
            created_at INTEGER NOT NULL, 
            FOREIGN KEY(pubkey) REFERENCES keys(pubkey) ON DELETE CASCADE
        );
        """
    )



async def m002_config(db):
    """
    Config table
    """
    await db.execute(
        """
        CREATE TABLE nwcprovider.config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """
    )

async def m003_default_config(db):
    """
    Default config
    """
    await db.execute(
        """
        INSERT INTO nwcprovider.config (key, value) VALUES ('relay', 'nostrclient');
        """
    )
    new_private_key = bytes.hex(secp256k1._gen_private_key())
    await db.execute(
        """
        INSERT INTO nwcprovider.config (key, value) VALUES ('provider_key', ?);
        """,
        (new_private_key,)
    )



async def m004_default_config2(db):
    """
    Default config
    """
  
    await db.execute(
        """
        INSERT INTO nwcprovider.config (key, value) VALUES ('relay_alias', ?);
        """,
        ('',)
    )


async def m005_key_last_used(db):
    """
    Add last_used to keys
    """
    await db.execute(
        """
        ALTER TABLE nwcprovider.keys ADD COLUMN last_used INTEGER;
        """
    )
