import json
import sqlite3
import logging
from logging.handlers import RotatingFileHandler
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Internal modules
from SokUser import SokUser
from Colored import Colored

# --- 1. IMPROVED LOGGING SETUP ---
# Create the rotation handler (5MB per file, keep 2 backups)
log_file = "session_history.log"
handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=2)

# Create a format for the logs (Timestamp - Name - Level - Message)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)

# Set up the root logger to use our handler
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(handler)

# HIJACK UVICORN: Force Uvicorn's internal logs into our file handler
for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
    uv_logger = logging.getLogger(logger_name)
    uv_logger.handlers = [handler]
    uv_logger.propagate = False

# Create a specific logger for your app logic
logger = logging.getLogger("CepteSok")


# --- 2. DATABASE LOGIC ---
def getDbConnection():
    conn = sqlite3.connect("users.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


# Create table on startup
with getDbConnection() as conn:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS accounts (
            phoneNumber     TEXT    NOT NULL PRIMARY KEY,
            name            TEXT    NOT NULL,
            surname         TEXT    NOT NULL,
            email           TEXT    NOT NULL,
            accessToken     TEXT    NOT NULL UNIQUE,
            refreshToken    TEXT    NOT NULL,
            balance         REAL DEFAULT 0.0
        )
        """
    )


def saveToDB(user):
    conn = getDbConnection()
    conn.execute(
        """
            REPLACE INTO accounts (
                phoneNumber, name, surname, email, accessToken, refreshToken, balance
            ) VALUES (?, ?, ?, ?, ?, ?, ?);
        """,
        user.userTuple,
    )
    conn.commit()
    logger.info(f"Database: Saved/Updated user {user.phoneNumber}")


def updateTokens():
    conn = getDbConnection()
    users = conn.execute("SELECT * FROM accounts").fetchall()
    brokenUsers = []
    for user in users:
        sokUser = SokUser(*user)
        # Use logger instead of print
        logger.info(f"Updating token for: {sokUser.name}")
        if sokUser.updateToken():
            saveToDB(sokUser)
        else:
            brokenUsers.append(user)
            logger.warning(f"Failed to update token for: {sokUser.phoneNumber}")
    conn.close()
    return brokenUsers


# --- 3. API SETUP ---
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/user/{phoneNumber}")
def getUserFromPhone(phoneNumber: str):
    conn = getDbConnection()
    row = conn.execute(
        "SELECT * FROM accounts WHERE phoneNumber = ?", (phoneNumber,)
    ).fetchone()
    conn.close()

    if not row:
        logger.warning(f"API: User not found -> {phoneNumber}")
        raise HTTPException(status_code=404, detail="USER_NOT_FOUND")

    user = SokUser(*row)
    qrCode = user.fetchQR()
    logger.info(f"API: Fetched QR for {phoneNumber}")
    return {"qrCode": qrCode}


@app.post("/user/{phoneNumber}/login")
def loginUserWithPhone(phoneNumber: str):
    try:
        user = SokUser(phoneNumber)
        verificationId = user._requestLoginOTP()

        if verificationId == "BUYER_NOT_FOUND_EXCEPTION":
            logger.error(f"Login: Account not found for {phoneNumber}")
            raise HTTPException(status_code=404, detail="ACCOUNT_NOT_FOUND")

        if not verificationId:
            raise HTTPException(
                status_code=500,
                detail="Failed to get verification ID. Server returned None.",
            )

        logger.info(f"Login: OTP requested for {phoneNumber}. ID: {verificationId}")
        return {"verificationId": verificationId}

    except Exception as e:
        logger.error(f"CRASH in loginUserWithPhone: {str(e)}")
        # This will forcefully print the exact Python error onto your Swagger UI screen
        raise HTTPException(status_code=500, detail=f"INTERNAL_CRASH: {str(e)}")


@app.post("/user/{phoneNumber}/login/{verificationId}/{otpCode}")
def submitOTPCode(phoneNumber, verificationId, otpCode):
    user = SokUser(phoneNumber)
    authCode = user._submitOTP(verificationId, otpCode)

    if authCode == "BAD_REQUEST_EXCEPTION":
        logger.warning(f"Login: Incorrect OTP for {phoneNumber}")
        raise HTTPException(status_code=403, detail="INCORRECT_OTP")

    user.login(authCode)
    saveToDB(user)
    qrCode = user.fetchQR()
    logger.info(f"Login: Success for {phoneNumber}")
    return {"qrCode": qrCode}


@app.get("/user/index/{index}")
def getUserOfIndex(index: int):
    conn = getDbConnection()
    row = conn.execute(
        "SELECT * FROM accounts ORDER BY phoneNumber ASC LIMIT 1 OFFSET ?", (index - 1,)
    ).fetchone()
    conn.close()

    if not row:
        logger.warning(f"API: Index not found -> {index}")
        raise HTTPException(status_code=404, detail="INDEX_NOT_FOUND")

    user = SokUser(*row)
    qrCode = user.fetchQR()

    # Replaced print with logger
    logger.info(f"API: Index {index} access. QR Result: {qrCode}")

    if qrCode == "UNAUTHORIZED_EXCEPTION":
        logger.error(f"API: Unauthorized token for {user.phoneNumber}")
        raise HTTPException(status_code=403, detail="UNAUTHORIZED_EXCEPTION")

    return {"qrCode": qrCode}


@app.post("/update")
def updateAllUsers():
    logger.info("API: Global token update triggered.")
    brokenUsers = updateTokens()

    if brokenUsers:
        return {
            "brokenUsers": [
                {"phoneNumber": info[0], "name": info[1], "surname": info[2]}
                for info in brokenUsers
            ]
        }
    return {"updateSuccess": True}


@app.get("/count")
def getUserCount():
    conn = getDbConnection()
    userCount = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
    conn.close()
    return {"userCount": userCount}


if __name__ == "__main__":
    import uvicorn

    # log_level="info" here is fine because we've redirected the handlers above
    uvicorn.run(app, host="127.0.0.1", port=2828, log_level="info")
