#!/usr/bin/env python3
"""
Generate sample ticket dataset for deduptickets.

Creates 500 realistic support tickets with Filipino customer data
for January 2026, following the Ticket model schema.
"""

from __future__ import annotations

import json
import random
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from faker import Faker

# Initialize Faker with Filipino locale
fake = Faker(["fil_PH", "en_PH"])
Faker.seed(42)
random.seed(42)

# ============================================================================
# CONFIGURATION
# ============================================================================

TOTAL_TICKETS = 500
START_DATE = datetime(2026, 1, 1, 0, 0, 0)
END_DATE = datetime(2026, 1, 31, 23, 59, 59)

# Status distribution: 60% open, 20% pending, 15% resolved, 5% closed
STATUS_WEIGHTS = {
    "open": 0.60,
    "pending": 0.20,
    "resolved": 0.15,
    "closed": 0.05,
}

# Priority distribution
PRIORITY_WEIGHTS = {
    "low": 0.15,
    "medium": 0.50,
    "high": 0.25,
    "urgent": 0.10,
}

# Severity distribution (only for high/urgent priority)
SEVERITY_OPTIONS = ["S1", "S2", "S3", "S4", None]
SEVERITY_WEIGHTS = [0.05, 0.15, 0.30, 0.30, 0.20]

# Channels
CHANNELS = ["InApp", "Chat", "Email", "Social", "Phone"]
CHANNEL_WEIGHTS = [0.40, 0.25, 0.15, 0.10, 0.10]

# Account types
ACCOUNT_TYPES = ["Verified", "Basic", "Premium", None]
ACCOUNT_TYPE_WEIGHTS = [0.50, 0.30, 0.15, 0.05]

# Philippine regions and cities
REGIONS_CITIES = {
    "NCR": ["Makati", "Quezon City", "Manila", "Pasig", "Taguig", "Mandaluyong", "Parañaque"],
    "CALABARZON": ["Cavite", "Laguna", "Batangas", "Rizal", "Lucena"],
    "Central Luzon": ["Pampanga", "Bulacan", "Tarlac", "Nueva Ecija", "Angeles"],
    "VISAYAS": ["Cebu City", "Iloilo City", "Bacolod", "Tacloban", "Dumaguete"],
    "MINDANAO": ["Davao City", "Cagayan de Oro", "General Santos", "Zamboanga", "Butuan"],
    "Cordillera": ["Baguio", "La Trinidad", "Tabuk"],
    "Ilocos": ["Laoag", "Vigan", "San Fernando"],
}

# Weighted region distribution (NCR and CALABARZON more common)
REGION_WEIGHTS = {
    "NCR": 0.35,
    "CALABARZON": 0.20,
    "Central Luzon": 0.15,
    "VISAYAS": 0.12,
    "MINDANAO": 0.10,
    "Cordillera": 0.04,
    "Ilocos": 0.04,
}

# Common merchants and banks
MERCHANTS = [
    "BPI",
    "BDO",
    "Metrobank",
    "Landbank",
    "PNB",
    "Security Bank",
    "UnionBank",
    "RCBC",
    "Chinabank",
    "EastWest Bank",
    "7-Eleven",
    "SM Store",
    "Robinsons",
    "Mercury Drug",
    "Jollibee",
    "McDonald's",
    "Lazada",
    "Shopee",
    "Grab",
    "Food Panda",
]

# Telcos for load/mobile
TELCOS = ["Globe", "Smart", "DITO", "TNT", "TM", "Sun"]

# Partner outlets
PARTNER_OUTLETS = [
    "7-Eleven",
    "Cebuana Lhuillier",
    "M Lhuillier",
    "Palawan Express",
    "Bayad Center",
    "SM Bills Payment",
    "Robinsons Business Center",
]

# ============================================================================
# CATEGORY DEFINITIONS (from user's JSON)
# ============================================================================

CATEGORIES = {
    "AccountAccessAndLogin": {
        "weight": 0.08,
        "subcategories": [
            {
                "code": "LoginFailedInvalidCredentials",
                "label": "Login failed (invalid credentials)",
                "description": "User cannot log in due to incorrect PIN/password or credential mismatch.",
            },
            {
                "code": "LoginFailedOtpNotReceived",
                "label": "OTP not received",
                "description": "OTP/SMS verification code not received or delayed during login.",
            },
            {
                "code": "LoginFailedOtpInvalidOrExpired",
                "label": "OTP invalid/expired",
                "description": "OTP was entered but rejected as invalid or expired.",
            },
            {
                "code": "AccountLockedTooManyAttempts",
                "label": "Account locked (too many attempts)",
                "description": "Account locked after too many login/OTP/PIN failures.",
            },
            {
                "code": "ForgotPinResetFailed",
                "label": "Forgot PIN / reset failed",
                "description": "Customer cannot complete PIN reset flow.",
            },
            {
                "code": "DeviceBindingFailed",
                "label": "Device binding failed",
                "description": "Device enrollment/binding fails or cannot bind new device.",
            },
            {
                "code": "NewDeviceLoginBlocked",
                "label": "New device login blocked",
                "description": "Login blocked due to risk checks or policy when using a new device.",
            },
            {
                "code": "SessionTimeoutOrLoop",
                "label": "Session timeout / login loop",
                "description": "Login loops, session expires immediately, or stuck on loading.",
            },
            {
                "code": "BiometricLoginNotWorking",
                "label": "Biometric login not working",
                "description": "Face/Touch ID fails or not offered.",
            },
            {
                "code": "AccountDisabledOrSuspended",
                "label": "Account disabled/suspended",
                "description": "Account is suspended/disabled; user cannot access wallet.",
            },
            {
                "code": "AppInstallUpdateIssue",
                "label": "App install/update issue",
                "description": "Cannot install/update the app; blocked at store or update step.",
            },
        ],
    },
    "VerificationKyc": {
        "weight": 0.05,
        "subcategories": [
            {
                "code": "KycIdUploadFailed",
                "label": "ID upload failed",
                "description": "User cannot upload ID image or it fails validation.",
            },
            {
                "code": "KycSelfieLivenessFailed",
                "label": "Selfie / liveness failed",
                "description": "Selfie capture/liveness check fails or times out.",
            },
            {
                "code": "KycVerificationRejected",
                "label": "Verification rejected",
                "description": "KYC rejected due to mismatched info, unclear ID, or policy rules.",
            },
            {
                "code": "KycVerificationPendingTooLong",
                "label": "Verification pending too long",
                "description": "KYC status stuck in pending beyond expected timeframe.",
            },
            {
                "code": "KycNameOrBirthdateMismatch",
                "label": "Name/birthdate mismatch",
                "description": "Customer details do not match ID or records.",
            },
            {
                "code": "KycAddressValidationIssue",
                "label": "Address validation issue",
                "description": "Address cannot be validated; region/city mismatch or invalid format.",
            },
            {
                "code": "KycInvalidIdTypeOrExpired",
                "label": "Invalid/expired ID",
                "description": "ID type not accepted or ID expired.",
            },
            {
                "code": "KycDuplicateAccountDetected",
                "label": "Duplicate account detected",
                "description": "System flags potential duplicate identity/account.",
            },
            {
                "code": "KycUnderageOrEligibility",
                "label": "Underage / eligibility issue",
                "description": "Customer fails eligibility rules (age, residency, etc.).",
            },
            {
                "code": "KycDataCorrectionRequest",
                "label": "Request to correct KYC details",
                "description": "Customer requests update/correction to verified personal info.",
            },
            {
                "code": "KycConsentOrTermsIssue",
                "label": "Consent/terms issue",
                "description": "Cannot proceed due to consent capture/terms acceptance problems.",
            },
        ],
    },
    "CashIn": {
        "weight": 0.15,
        "subcategories": [
            {
                "code": "CashInFailedButDebited",
                "label": "Cash-in failed but debited",
                "description": "Cash-in attempt failed yet source account/card/outlet shows a debit.",
            },
            {
                "code": "CashInSuccessNotCredited",
                "label": "Successful cash-in not credited",
                "description": "Partner shows success but wallet balance not credited.",
            },
            {
                "code": "CashInPendingOrDelayed",
                "label": "Cash-in pending/delayed",
                "description": "Cash-in remains pending beyond expected timeframe.",
            },
            {
                "code": "CashInReversed",
                "label": "Cash-in reversed",
                "description": "Cash-in credited then reversed/removed.",
            },
            {
                "code": "CashInLimitExceeded",
                "label": "Cash-in limit exceeded",
                "description": "Cash-in blocked due to daily/monthly limits.",
            },
            {
                "code": "CashInBankMaintenanceOrDown",
                "label": "Bank/partner maintenance or down",
                "description": "Cash-in fails due to partner system outage or maintenance.",
            },
            {
                "code": "CashInCardDeclined",
                "label": "Card cash-in declined",
                "description": "Card cash-in declined by issuer, risk rules, or authentication failure.",
            },
            {
                "code": "CashInOverTheCounterNotReceived",
                "label": "OTC cash-in not received",
                "description": "Over-the-counter cash-in paid at outlet but not credited.",
            },
            {
                "code": "CashInOverTheCounterWrongReference",
                "label": "OTC wrong reference/details",
                "description": "Outlet used wrong reference or customer details; cash-in misapplied.",
            },
            {
                "code": "CashInFeeChargedUnexpectedly",
                "label": "Unexpected cash-in fee",
                "description": "Customer disputes cash-in fee charged.",
            },
            {
                "code": "CashInChargebackOrDispute",
                "label": "Cash-in chargeback/dispute",
                "description": "Cash-in reversed due to dispute/chargeback from source.",
            },
        ],
    },
    "CashOut": {
        "weight": 0.10,
        "subcategories": [
            {
                "code": "CashOutFailedButDebited",
                "label": "Cash-out failed but debited",
                "description": "Cash-out fails but wallet balance decreased.",
            },
            {
                "code": "CashOutSuccessButNoDispense",
                "label": "ATM cash-out: no dispense",
                "description": "ATM transaction successful but cash not dispensed.",
            },
            {
                "code": "CashOutDispensedButStillDebitedTwice",
                "label": "ATM cash-out: double debit",
                "description": "Customer reports duplicated debit or repeated cash-out charge.",
            },
            {
                "code": "CashOutPendingOrDelayed",
                "label": "Cash-out pending/delayed",
                "description": "Cash-out stuck pending or delayed beyond expected timeframe.",
            },
            {
                "code": "CashOutReversalDelayed",
                "label": "Cash-out reversal delayed",
                "description": "Expected reversal after failed cash-out not received on time.",
            },
            {
                "code": "CashOutOtpOrCodeNotReceived",
                "label": "Cash-out code/OTP not received",
                "description": "Withdrawal code or OTP not received for OTC/partner cash-out.",
            },
            {
                "code": "CashOutInvalidOrExpiredCode",
                "label": "Cash-out code invalid/expired",
                "description": "Withdrawal code expired or invalid at outlet.",
            },
            {
                "code": "CashOutLimitExceeded",
                "label": "Cash-out limit exceeded",
                "description": "Blocked due to withdrawal limits.",
            },
            {
                "code": "CashOutFeeDispute",
                "label": "Cash-out fee dispute",
                "description": "Customer disputes withdrawal fee amount or unexpected charge.",
            },
            {
                "code": "CashOutPartnerOutletIssue",
                "label": "Partner outlet issue",
                "description": "Outlet cannot process cash-out due to system issues or policy mismatch.",
            },
        ],
    },
    "Transfers": {
        "weight": 0.15,
        "subcategories": [
            {
                "code": "P2PSentButNotReceived",
                "label": "P2P sent but not received",
                "description": "Sender shows success; recipient did not receive funds.",
            },
            {
                "code": "P2PFailedButDebited",
                "label": "P2P failed but debited",
                "description": "Transfer fails but sender balance decreased.",
            },
            {
                "code": "P2PWrongRecipient",
                "label": "Sent to wrong recipient",
                "description": "Customer claims transfer was sent to an incorrect account/number.",
            },
            {
                "code": "P2PRecipientNotFound",
                "label": "Recipient not found/invalid",
                "description": "Recipient identifier invalid or not registered.",
            },
            {
                "code": "BankTransferInstapayFailed",
                "label": "InstaPay transfer failed",
                "description": "InstaPay transfer fails before completion.",
            },
            {
                "code": "BankTransferInstapayPending",
                "label": "InstaPay pending/delayed credit",
                "description": "InstaPay sent but credit is delayed.",
            },
            {
                "code": "BankTransferPesonetPending",
                "label": "PESONet pending (batch)",
                "description": "PESONet transfer pending due to batch processing schedules.",
            },
            {
                "code": "BankTransferReversalOrReturned",
                "label": "Bank transfer returned/reversed",
                "description": "Transfer returned by receiving bank (invalid account, etc.).",
            },
            {
                "code": "BankTransferWrongAccountNumber",
                "label": "Wrong bank account number",
                "description": "Customer used incorrect destination account; needs guidance/dispute process.",
            },
            {
                "code": "TransferLimitOrComplianceBlock",
                "label": "Transfer blocked (limits/compliance)",
                "description": "Transfer prevented due to limits or compliance/risk flags.",
            },
            {
                "code": "TransferFeeDispute",
                "label": "Transfer fee dispute",
                "description": "Customer disputes transfer fee or unexpected charges.",
            },
        ],
    },
    "Payments": {
        "weight": 0.12,
        "subcategories": [
            {
                "code": "QrPaymentFailed",
                "label": "QR payment failed",
                "description": "QR merchant payment fails at scan/confirm stage.",
            },
            {
                "code": "QrPaymentSuccessButMerchantNotPaid",
                "label": "Paid but merchant not credited",
                "description": "Customer shows payment success but merchant reports no receipt.",
            },
            {
                "code": "OnlineCheckoutFailed",
                "label": "Online checkout failed",
                "description": "Payment fails on online checkout flow (in-app/web).",
            },
            {
                "code": "PaymentPendingOrProcessing",
                "label": "Payment pending/processing",
                "description": "Payment stuck pending beyond expected time.",
            },
            {
                "code": "DuplicatePayment",
                "label": "Duplicate payment",
                "description": "Customer charged twice or repeated payment created.",
            },
            {
                "code": "PaymentReversedOrRefundNeeded",
                "label": "Payment reversed/refund needed",
                "description": "Payment reversed or customer requests refund due to failure/issue.",
            },
            {
                "code": "MerchantDisputeWrongAmount",
                "label": "Wrong amount charged",
                "description": "Customer disputes incorrect amount at merchant.",
            },
            {
                "code": "MerchantNotFoundOrInvalidQr",
                "label": "Merchant not found / invalid QR",
                "description": "QR code invalid/expired or merchant not recognized.",
            },
            {
                "code": "PaymentDeclinedRiskOrLimit",
                "label": "Payment declined (risk/limit)",
                "description": "Payment declined due to risk checks, limits, or compliance rules.",
            },
            {
                "code": "PaymentFeeDispute",
                "label": "Payment fee dispute",
                "description": "Customer disputes fees or surcharges associated with payment.",
            },
        ],
    },
    "BillsPayment": {
        "weight": 0.10,
        "subcategories": [
            {
                "code": "BillsPaymentFailedButDebited",
                "label": "Bill payment failed but debited",
                "description": "Payment failed but wallet balance decreased.",
            },
            {
                "code": "BillsPaymentSuccessNotPosted",
                "label": "Paid but not posted to biller",
                "description": "Wallet shows success but biller does not reflect payment.",
            },
            {
                "code": "BillsPaymentPending",
                "label": "Bill payment pending/delayed",
                "description": "Payment pending due to biller processing delays.",
            },
            {
                "code": "BillsPaymentWrongAccountNumber",
                "label": "Wrong biller account number",
                "description": "Customer entered wrong account/reference number.",
            },
            {
                "code": "BillsPaymentDuplicate",
                "label": "Duplicate bill payment",
                "description": "Customer paid twice for same bill/account.",
            },
            {
                "code": "BillsPaymentPartialPosting",
                "label": "Partial posting",
                "description": "Only part of amount posted or mismatch in biller posting.",
            },
            {
                "code": "BillerUnavailableOrMaintenance",
                "label": "Biller unavailable/maintenance",
                "description": "Biller system down or unavailable.",
            },
            {
                "code": "BillsPaymentFeeDispute",
                "label": "Bills payment fee dispute",
                "description": "Customer disputes convenience fee or unexpected charges.",
            },
            {
                "code": "BillsPaymentRefundRequest",
                "label": "Bills payment refund request",
                "description": "Customer requests refund due to posting issues or wrong details.",
            },
        ],
    },
    "BuyLoadMobileTopUp": {
        "weight": 0.06,
        "subcategories": [
            {
                "code": "LoadPurchaseFailedButDebited",
                "label": "Load failed but debited",
                "description": "Top-up failed but wallet charged.",
            },
            {
                "code": "LoadSuccessNotReceived",
                "label": "Load not received",
                "description": "Top-up shows success but subscriber did not receive load.",
            },
            {
                "code": "LoadDelayed",
                "label": "Load delayed",
                "description": "Load delivery delayed beyond expected time.",
            },
            {
                "code": "LoadWrongNumber",
                "label": "Loaded wrong number",
                "description": "Customer loaded an incorrect mobile number.",
            },
            {
                "code": "LoadPromoNotApplied",
                "label": "Promo not applied",
                "description": "Top-up promo bundle not applied or incorrect denomination.",
            },
            {
                "code": "LoadTelcoMaintenance",
                "label": "Telco maintenance/outage",
                "description": "Top-up failures due to telco unavailability.",
            },
            {
                "code": "LoadLimitExceeded",
                "label": "Top-up limit exceeded",
                "description": "Blocked due to top-up limits or policy constraints.",
            },
            {
                "code": "LoadDuplicateCharge",
                "label": "Duplicate top-up charge",
                "description": "Customer charged twice for a top-up.",
            },
        ],
    },
    "Cards": {
        "weight": 0.04,
        "subcategories": [
            {
                "code": "CardActivationFailed",
                "label": "Card activation failed",
                "description": "Physical/virtual card activation fails.",
            },
            {
                "code": "CardPaymentDeclined",
                "label": "Card payment declined",
                "description": "Card transaction declined at merchant.",
            },
            {
                "code": "CardOnlinePayment3dsFailed",
                "label": "3DS/OTP failed for card payment",
                "description": "Authentication fails for online card payment.",
            },
            {
                "code": "CardCashWithdrawalFailed",
                "label": "Card cash withdrawal failed",
                "description": "ATM withdrawal using card fails.",
            },
            {
                "code": "CardChargeDispute",
                "label": "Card charge dispute",
                "description": "Customer disputes a card transaction as incorrect/unauthorized.",
            },
            {
                "code": "CardFrozenOrBlocked",
                "label": "Card frozen/blocked",
                "description": "Card is blocked or cannot be used; customer requests unblock.",
            },
            {
                "code": "CardReplacementRequest",
                "label": "Card replacement request",
                "description": "Customer requests replacement for lost/damaged card.",
            },
            {
                "code": "CardDeliveryIssue",
                "label": "Card delivery issue",
                "description": "Card delivery delayed, failed, or address issues.",
            },
            {
                "code": "CardTokenizationIssue",
                "label": "Card tokenization / wallet add failed",
                "description": "Adding card to external wallets (if applicable) fails.",
            },
            {
                "code": "CardFeeDispute",
                "label": "Card fee dispute",
                "description": "Customer disputes card-related fees (issuance, replacement, FX, etc.).",
            },
        ],
    },
    "RefundsReversalsDisputes": {
        "weight": 0.05,
        "subcategories": [
            {
                "code": "RefundNotReceived",
                "label": "Refund not received",
                "description": "Refund expected but not yet credited.",
            },
            {
                "code": "RefundDelayedBeyondSla",
                "label": "Refund delayed beyond SLA",
                "description": "Refund processing exceeds stated timelines.",
            },
            {
                "code": "ReversalPending",
                "label": "Reversal pending",
                "description": "Transaction reversal pending after a failed transaction.",
            },
            {
                "code": "ChargebackStatusInquiry",
                "label": "Chargeback status inquiry",
                "description": "Customer asks status of dispute/chargeback process.",
            },
            {
                "code": "DisputeFiledUnauthorized",
                "label": "Dispute filed: unauthorized",
                "description": "Customer disputes a transaction as unauthorized.",
            },
            {
                "code": "DisputeFiledServiceNotReceived",
                "label": "Dispute filed: goods/service not received",
                "description": "Customer claims merchant service not delivered.",
            },
            {
                "code": "DisputeDuplicateCharge",
                "label": "Dispute: duplicate charge",
                "description": "Customer disputes duplicate billing for same purchase.",
            },
            {
                "code": "DisputeWrongAmount",
                "label": "Dispute: wrong amount",
                "description": "Customer disputes incorrect amount charged.",
            },
            {
                "code": "DisputeEvidenceRequest",
                "label": "Dispute: evidence requested",
                "description": "Support requests evidence/docs from customer for dispute processing.",
            },
            {
                "code": "RefundPartial",
                "label": "Partial refund",
                "description": "Refund amount is partial or mismatched.",
            },
        ],
    },
    "FraudScamUnauthorized": {
        "weight": 0.03,
        "subcategories": [
            {
                "code": "UnauthorizedTransfer",
                "label": "Unauthorized transfer",
                "description": "Customer reports transfer they did not authorize.",
            },
            {
                "code": "UnauthorizedPayment",
                "label": "Unauthorized payment",
                "description": "Customer reports unauthorized merchant/QR/online payment.",
            },
            {
                "code": "AccountTakeoverSuspected",
                "label": "Account takeover suspected",
                "description": "Customer suspects account was accessed by someone else.",
            },
            {
                "code": "PhishingOrSocialEngineering",
                "label": "Phishing/social engineering report",
                "description": "Customer reports scam links, phishing, or social engineering.",
            },
            {
                "code": "SimSwapSuspected",
                "label": "SIM swap suspected",
                "description": "Customer suspects SIM swap leading to OTP compromise.",
            },
            {
                "code": "DeviceCompromised",
                "label": "Device compromised / malware",
                "description": "Suspected malware or compromised device behavior.",
            },
            {
                "code": "ScamMerchantOrBiller",
                "label": "Scam merchant/biller report",
                "description": "Customer reports scam merchant/biller transaction.",
            },
            {
                "code": "MoneyMuleOrSuspiciousActivity",
                "label": "Suspicious activity / money mule",
                "description": "Patterns suggesting mule activity, rapid transfers, unusual behavior.",
            },
            {
                "code": "FraudInvestigationStatus",
                "label": "Fraud investigation status inquiry",
                "description": "Customer asks for case updates on fraud investigation.",
            },
            {
                "code": "SecurityHoldOrFreeze",
                "label": "Security hold/freeze",
                "description": "Account or funds placed on hold for security review.",
            },
        ],
    },
    "LimitsFeesPricing": {
        "weight": 0.03,
        "subcategories": [
            {
                "code": "DailyMonthlyLimitExceeded",
                "label": "Daily/monthly limit exceeded",
                "description": "Customer hits transaction limits (cash-in/out/transfer/payment).",
            },
            {
                "code": "TierUpgradeRequired",
                "label": "Tier upgrade required",
                "description": "Action blocked until verification/tier upgrade is completed.",
            },
            {
                "code": "FeeChargedUnexpectedly",
                "label": "Unexpected fee charged",
                "description": "Customer disputes a fee that they did not expect.",
            },
            {
                "code": "FeeComputationQuestion",
                "label": "Fee computation question",
                "description": "Customer asks how fees are computed or why fee differs.",
            },
            {
                "code": "PricingPolicyChangeInquiry",
                "label": "Pricing/policy change inquiry",
                "description": "Customer asks about changes in limits/fees/policies.",
            },
            {
                "code": "RefundOfFeesRequest",
                "label": "Request fee refund",
                "description": "Customer requests reversal/refund of fees.",
            },
            {
                "code": "ComplianceLimitBlock",
                "label": "Compliance-related block",
                "description": "Limits triggered due to compliance/risk controls.",
            },
        ],
    },
    "PromosRewardsPoints": {
        "weight": 0.02,
        "subcategories": [
            {
                "code": "CashbackMissing",
                "label": "Cashback missing",
                "description": "Cashback not received after eligible transaction.",
            },
            {
                "code": "PromoNotApplied",
                "label": "Promo not applied",
                "description": "Promo conditions met but not applied at checkout.",
            },
            {
                "code": "VoucherInvalidOrExpired",
                "label": "Voucher invalid/expired",
                "description": "Voucher code not accepted or is expired.",
            },
            {
                "code": "RewardsNotCredited",
                "label": "Rewards/points not credited",
                "description": "Points not credited or delayed.",
            },
            {
                "code": "RewardsBalanceMismatch",
                "label": "Rewards balance mismatch",
                "description": "Points balance appears incorrect.",
            },
            {
                "code": "PromoEligibilityDispute",
                "label": "Eligibility dispute",
                "description": "Customer disputes eligibility decision for promo/reward.",
            },
            {
                "code": "PromoFraudAbuseFlag",
                "label": "Promo abuse/fraud flag",
                "description": "Promo blocked due to abuse detection or policy constraints.",
            },
        ],
    },
    "AppTechnicalPerformance": {
        "weight": 0.04,
        "subcategories": [
            {
                "code": "AppCrash",
                "label": "App crash",
                "description": "App crashes on launch or during key flows.",
            },
            {
                "code": "AppSlowOrLag",
                "label": "App slow/lag",
                "description": "Performance degradation, slow screens, long loading times.",
            },
            {
                "code": "BlankScreenOrStuckLoading",
                "label": "Blank screen / stuck loading",
                "description": "App stuck loading or shows blank screen.",
            },
            {
                "code": "PaymentFlowUiError",
                "label": "Payment flow UI error",
                "description": "UI/UX errors during payment flows (buttons disabled, validation issues).",
            },
            {
                "code": "PushNotificationNotWorking",
                "label": "Push notification not working",
                "description": "Notifications not received or delayed.",
            },
            {
                "code": "NetworkConnectivityIssue",
                "label": "Connectivity/network issue",
                "description": "App cannot connect or fails depending on network type.",
            },
            {
                "code": "MaintenanceBannerOrDowntime",
                "label": "Maintenance/downtime",
                "description": "Service unavailable due to maintenance or outage.",
            },
            {
                "code": "CompatibilityIssueDeviceOs",
                "label": "Device/OS compatibility issue",
                "description": "App not supported or unstable on certain devices/OS versions.",
            },
            {
                "code": "InAppCameraOrPermissionIssue",
                "label": "Camera/permission issue",
                "description": "Camera, storage, location permissions block app features.",
            },
        ],
    },
    "ProfileAndSettings": {
        "weight": 0.02,
        "subcategories": [
            {
                "code": "ChangeMobileNumberRequest",
                "label": "Change mobile number request",
                "description": "Customer wants to update their registered mobile number.",
            },
            {
                "code": "EmailUpdateRequest",
                "label": "Update email request",
                "description": "Customer wants to update email address.",
            },
            {
                "code": "NameCorrectionRequest",
                "label": "Name correction request",
                "description": "Customer requests correction of profile/KYC name details.",
            },
            {
                "code": "AddressUpdateRequest",
                "label": "Update address request",
                "description": "Customer requests address changes in profile/KYC.",
            },
            {
                "code": "NotificationPreferenceIssue",
                "label": "Notification preference issue",
                "description": "Customer cannot change notification preferences or settings don't persist.",
            },
            {
                "code": "AccountClosureRequest",
                "label": "Account closure request",
                "description": "Customer requests account closure/deactivation.",
            },
            {
                "code": "DataPrivacyRequest",
                "label": "Data/privacy request",
                "description": "Customer requests data access/deletion or privacy-related action.",
            },
        ],
    },
    "PartnerMerchantBankIntegration": {
        "weight": 0.02,
        "subcategories": [
            {
                "code": "PartnerOutageSuspected",
                "label": "Partner outage suspected",
                "description": "Multiple failures tied to a specific partner (bank/merchant/biller).",
            },
            {
                "code": "PartnerTimeoutOrLatency",
                "label": "Partner timeout/latency",
                "description": "Requests time out or complete slowly due to partner latency.",
            },
            {
                "code": "PartnerSettlementOrPostingDelay",
                "label": "Settlement/posting delay",
                "description": "Delays between wallet success and partner posting/settlement.",
            },
            {
                "code": "PartnerConfigurationMismatch",
                "label": "Configuration mismatch",
                "description": "Incorrect routing codes, bank codes, merchant profiles, or config drift.",
            },
            {
                "code": "PartnerDisputeOrChargebackFlow",
                "label": "Partner dispute/chargeback flow issue",
                "description": "Dispute/refund processes stuck due to partner workflow.",
            },
            {
                "code": "PartnerFeeMismatch",
                "label": "Partner fee mismatch",
                "description": "Fees differ due to partner policy changes or incorrect fee tables.",
            },
            {
                "code": "PartnerReferenceValidationError",
                "label": "Reference validation error",
                "description": "Partner rejects due to invalid reference/account format.",
            },
        ],
    },
    "CustomerSupportGeneralInquiry": {
        "weight": 0.02,
        "subcategories": [
            {
                "code": "HowToQuestion",
                "label": "How-to question",
                "description": "Customer asks how to use a feature (cash-in, transfer, QR, etc.).",
            },
            {
                "code": "StatusFollowUp",
                "label": "Status follow-up",
                "description": "Customer follows up on an existing ticket or pending transaction.",
            },
            {
                "code": "AccountTierBenefitsInquiry",
                "label": "Account tier/benefits inquiry",
                "description": "Customer asks about tiers, benefits, and requirements.",
            },
            {
                "code": "ComplaintGeneral",
                "label": "General complaint",
                "description": "Complaint not clearly tied to a specific transaction category.",
            },
            {
                "code": "FeedbackSuggestion",
                "label": "Feedback/suggestion",
                "description": "Customer provides feedback or feature suggestions.",
            },
        ],
    },
}

# Categories that typically have transaction amounts
FINANCIAL_CATEGORIES = [
    "CashIn",
    "CashOut",
    "Transfers",
    "Payments",
    "BillsPayment",
    "BuyLoadMobileTopUp",
    "Cards",
    "RefundsReversalsDisputes",
]

# ============================================================================
# KEY CONVERSION
# ============================================================================

_SNAKE_RE = re.compile(r"_([a-z])")


def _snake_to_camel(name: str) -> str:
    """Convert a snake_case string to camelCase."""
    return _SNAKE_RE.sub(lambda m: m.group(1).upper(), name)


def _convert_keys_to_camel(record: dict[str, Any]) -> dict[str, Any]:
    """Rename all snake_case keys in a ticket dict to camelCase."""
    return {_snake_to_camel(k): v for k, v in record.items()}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def weighted_choice(options: dict[str, float]) -> str:
    """Select from weighted options."""
    items = list(options.keys())
    weights = list(options.values())
    return random.choices(items, weights=weights, k=1)[0]


def generate_customer_id() -> str:
    """Generate a customer ID."""
    return f"CUST-{random.randint(1000000, 9999999)}"


def generate_mobile_number() -> str:
    """Generate a Philippine mobile number."""
    prefix = random.choice(
        [
            "0917",
            "0918",
            "0919",
            "0920",
            "0921",
            "0927",
            "0928",
            "0929",
            "0930",
            "0938",
            "0939",
            "0949",
            "0951",
            "0961",
            "0991",
            "0999",
        ]
    )
    return f"{prefix}{random.randint(1000000, 9999999)}"


def generate_email(name: str) -> str:
    """Generate an email from name."""
    domains = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "protonmail.com"]
    clean_name = name.lower().replace(" ", ".").replace(",", "")
    return f"{clean_name}{random.randint(1, 999)}@{random.choice(domains)}"


def generate_transaction_id() -> str:
    """Generate a transaction ID."""
    return f"TXN-{uuid4().hex[:12].upper()}"


def generate_amount(category: str) -> float | None:
    """Generate a realistic PHP amount based on category."""
    if category not in FINANCIAL_CATEGORIES:
        return None

    # Different amount ranges for different categories
    ranges = {
        "CashIn": (100, 50000),
        "CashOut": (100, 30000),
        "Transfers": (50, 50000),
        "Payments": (50, 10000),
        "BillsPayment": (100, 15000),
        "BuyLoadMobileTopUp": (10, 1000),
        "Cards": (100, 25000),
        "RefundsReversalsDisputes": (50, 20000),
    }

    min_amt, max_amt = ranges.get(category, (50, 10000))

    # Common amounts (round numbers more likely)
    if random.random() < 0.4:
        common = [100, 200, 300, 500, 1000, 1500, 2000, 2500, 3000, 5000, 10000, 15000, 20000]
        return float(random.choice([a for a in common if min_amt <= a <= max_amt]))

    return round(random.uniform(min_amt, max_amt), 2)


def generate_summary_variations(subcategory: dict, category: str) -> list[str]:
    """Generate summary variations for a subcategory."""
    label = subcategory["label"]

    # Base templates
    templates = [
        f"{label}",
        f"{label} - need help",
        f"Issue: {label}",
        f"Problem with {label.lower()}",
        f"{label} - please assist",
        f"Concern: {label}",
        f"{label} happened today",
        f"Having trouble - {label.lower()}",
        f"Help needed: {label}",
        f"{label} issue reported",
    ]

    # Add category-specific variations
    if category in FINANCIAL_CATEGORIES:
        amount = random.randint(100, 5000)
        templates.extend(
            [
                f"{label} - PHP {amount}",
                f"{label} for PHP {amount} transaction",
                f"PHP {amount} {label.lower()}",
            ]
        )

    return templates


def generate_description(
    subcategory: dict, summary: str, category: str, amount: float | None
) -> str:
    """Generate a detailed description."""
    base_desc = subcategory["description"]

    details = [base_desc]

    # Add contextual details
    if amount:
        details.append(f"Amount involved: PHP {amount:,.2f}")

    if category in ["CashIn", "CashOut", "Transfers"]:
        details.append(f"Partner/Bank: {random.choice(MERCHANTS)}")

    if "OTP" in summary or "otp" in summary.lower():
        details.append(f"Telco: {random.choice(TELCOS)}")

    if random.random() < 0.3:
        details.append("Customer is requesting urgent resolution.")

    if random.random() < 0.2:
        details.append("This is a follow-up to a previous ticket.")

    return " ".join(details)


def random_datetime_in_range(start: datetime, end: datetime) -> datetime:
    """Generate a random datetime within range."""
    delta = end - start
    random_seconds = random.randint(0, int(delta.total_seconds()))
    return start + timedelta(seconds=random_seconds)


def select_region_city() -> tuple[str, str]:
    """Select a region and city."""
    region = weighted_choice(REGION_WEIGHTS)
    city = random.choice(REGIONS_CITIES[region])
    return region, city


# ============================================================================
# TICKET GENERATION
# ============================================================================


def generate_base_ticket(ticket_number: int, created_at: datetime) -> dict:
    """Generate a base ticket with customer info."""
    _region, _city = select_region_city()
    name = fake.name()

    return {
        "id": str(uuid4()),
        "pk": created_at.strftime("%Y-%m"),
        "ticket_number": f"#{100000 + ticket_number}",
        "created_at": created_at.isoformat(),
        "updated_at": created_at.isoformat(),
        "closed_at": None,
        "status": weighted_choice(STATUS_WEIGHTS),
        "priority": weighted_choice(PRIORITY_WEIGHTS),
        "severity": random.choices(SEVERITY_OPTIONS, weights=SEVERITY_WEIGHTS, k=1)[0],
        "channel": random.choices(CHANNELS, weights=CHANNEL_WEIGHTS, k=1)[0],
        "customer_id": generate_customer_id(),
        "name": name,
        "mobile_number": generate_mobile_number(),
        "email": generate_email(name),
        "account_type": random.choices(ACCOUNT_TYPES, weights=ACCOUNT_TYPE_WEIGHTS, k=1)[0],
        "category": None,
        "subcategory": None,
        "summary": None,
        "description": None,
        "transaction_id": None,
        "amount": None,
        "currency": "PHP",
        "merchant": None,
        "occurred_at": None,
        "merged_into_id": None,
        "cluster_id": None,
        "raw_metadata": None,
    }


def generate_ticket(ticket_number: int) -> dict:
    """Generate a single ticket."""
    created_at = random_datetime_in_range(START_DATE, END_DATE)
    ticket = generate_base_ticket(ticket_number, created_at)

    # Select category based on weights
    category = weighted_choice({cat: data["weight"] for cat, data in CATEGORIES.items()})
    subcategory_data = random.choice(CATEGORIES[category]["subcategories"])

    ticket["category"] = category
    ticket["subcategory"] = subcategory_data["code"]

    # Generate summary and description
    summaries = generate_summary_variations(subcategory_data, category)
    ticket["summary"] = random.choice(summaries)

    # Generate amount for financial categories
    amount = generate_amount(category)
    ticket["amount"] = amount

    ticket["description"] = generate_description(
        subcategory_data, ticket["summary"], category, amount
    )

    # Add transaction details for financial categories
    if category in FINANCIAL_CATEGORIES:
        ticket["transaction_id"] = generate_transaction_id()
        ticket["merchant"] = random.choice(MERCHANTS)
        ticket["occurred_at"] = (created_at - timedelta(hours=random.randint(1, 48))).isoformat()

    # Set closed_at for resolved/closed tickets
    if ticket["status"] in ["resolved", "closed"]:
        resolution_time = timedelta(hours=random.randint(1, 72))
        ticket["closed_at"] = (created_at + resolution_time).isoformat()
        ticket["updated_at"] = ticket["closed_at"]

    return ticket


def generate_similar_ticket(base_ticket: dict, ticket_number: int) -> dict:
    """Generate a ticket similar to base (same subcategory, rephrased summary)."""
    created_at = random_datetime_in_range(START_DATE, END_DATE)
    ticket = generate_base_ticket(ticket_number, created_at)

    # Copy category/subcategory
    ticket["category"] = base_ticket["category"]
    ticket["subcategory"] = base_ticket["subcategory"]

    # Get subcategory data for generating new summary
    subcategory_data = next(
        (
            s
            for s in CATEGORIES[ticket["category"]]["subcategories"]
            if s["code"] == ticket["subcategory"]
        ),
        None,
    )

    if subcategory_data:
        summaries = generate_summary_variations(subcategory_data, ticket["category"])
        # Pick a different summary than the base
        available = [s for s in summaries if s != base_ticket["summary"]]
        ticket["summary"] = random.choice(available) if available else random.choice(summaries)

        amount = generate_amount(ticket["category"])
        ticket["amount"] = amount
        ticket["description"] = generate_description(
            subcategory_data, ticket["summary"], ticket["category"], amount
        )

    # Add transaction details for financial categories
    if ticket["category"] in FINANCIAL_CATEGORIES:
        ticket["transaction_id"] = generate_transaction_id()
        ticket["merchant"] = random.choice(MERCHANTS)
        ticket["occurred_at"] = (created_at - timedelta(hours=random.randint(1, 48))).isoformat()

    if ticket["status"] in ["resolved", "closed"]:
        resolution_time = timedelta(hours=random.randint(1, 72))
        ticket["closed_at"] = (created_at + resolution_time).isoformat()
        ticket["updated_at"] = ticket["closed_at"]

    return ticket


def generate_exact_duplicate(base_ticket: dict, ticket_number: int) -> dict:
    """Generate an exact duplicate (same customer, similar summary)."""
    created_at = random_datetime_in_range(START_DATE, END_DATE)

    ticket = {
        "id": str(uuid4()),
        "pk": created_at.strftime("%Y-%m"),
        "ticket_number": f"#{100000 + ticket_number}",
        "created_at": created_at.isoformat(),
        "updated_at": created_at.isoformat(),
        "closed_at": None,
        "status": weighted_choice(STATUS_WEIGHTS),
        "priority": base_ticket["priority"],
        "severity": base_ticket["severity"],
        "channel": base_ticket["channel"],
        # Same customer details
        "customer_id": base_ticket["customer_id"],
        "name": base_ticket["name"],
        "mobile_number": base_ticket["mobile_number"],
        "email": base_ticket["email"],
        "account_type": base_ticket["account_type"],
        # Same issue
        "category": base_ticket["category"],
        "subcategory": base_ticket["subcategory"],
        "summary": base_ticket["summary"],  # Exact same summary
        "description": base_ticket["description"] + " (Follow-up submission)",
        "transaction_id": base_ticket.get("transaction_id"),
        "amount": base_ticket.get("amount"),
        "currency": "PHP",
        "merchant": base_ticket.get("merchant"),
        "occurred_at": base_ticket.get("occurred_at"),
        "merged_into_id": None,
        "cluster_id": None,
        "raw_metadata": None,
    }

    if ticket["status"] in ["resolved", "closed"]:
        resolution_time = timedelta(hours=random.randint(1, 72))
        ticket["closed_at"] = (created_at + resolution_time).isoformat()
        ticket["updated_at"] = ticket["closed_at"]

    return ticket


def generate_dataset() -> list[dict]:
    """Generate the full dataset of 500 tickets."""
    tickets = []
    ticket_number = 1

    # Calculate distribution
    # 80% unique, 15% similar, 5% exact duplicates
    unique_count = int(TOTAL_TICKETS * 0.80)
    similar_count = int(TOTAL_TICKETS * 0.15)
    duplicate_count = TOTAL_TICKETS - unique_count - similar_count

    print(f"Generating {unique_count} unique tickets...")
    unique_tickets = []
    for _ in range(unique_count):
        ticket = generate_ticket(ticket_number)
        tickets.append(ticket)
        unique_tickets.append(ticket)
        ticket_number += 1

    print(f"Generating {similar_count} similar tickets (rephrased)...")
    for _ in range(similar_count):
        base = random.choice(unique_tickets)
        ticket = generate_similar_ticket(base, ticket_number)
        tickets.append(ticket)
        ticket_number += 1

    print(f"Generating {duplicate_count} exact duplicate tickets...")
    for _ in range(duplicate_count):
        base = random.choice(unique_tickets)
        ticket = generate_exact_duplicate(base, ticket_number)
        tickets.append(ticket)
        ticket_number += 1

    # Shuffle to mix ticket types
    random.shuffle(tickets)

    # Reassign ticket numbers in order
    for i, ticket in enumerate(tickets):
        ticket["ticket_number"] = f"#{100001 + i}"

    return tickets


def main() -> None:
    """Main entry point."""
    print("=" * 60)
    print("Generating Sample Tickets Dataset")
    print("=" * 60)
    print(f"Total tickets: {TOTAL_TICKETS}")
    print(f"Date range: {START_DATE.date()} to {END_DATE.date()}")
    print()

    tickets = generate_dataset()

    # Create output directory
    output_dir = Path(__file__).parent.parent / "data"
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / "sample_tickets.json"

    # Convert keys to camelCase for Cosmos DB compatibility
    tickets = [_convert_keys_to_camel(t) for t in tickets]

    # Write to file
    with output_file.open("w", encoding="utf-8") as f:
        json.dump(tickets, f, indent=2, ensure_ascii=False)

    print()
    print("=" * 60)
    print("Dataset generated successfully!")
    print(f"Output: {output_file}")
    print(f"Total tickets: {len(tickets)}")
    print()

    # Print category distribution
    category_counts: dict[str, int] = {}
    for ticket in tickets:
        cat = ticket["category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1

    print("Category Distribution:")
    for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
        pct = count / len(tickets) * 100
        print(f"  {cat}: {count} ({pct:.1f}%)")

    # Print status distribution
    status_counts: dict[str, int] = {}
    for ticket in tickets:
        status = ticket["status"]
        status_counts[status] = status_counts.get(status, 0) + 1

    print()
    print("Status Distribution:")
    for status, count in sorted(status_counts.items(), key=lambda x: -x[1]):
        pct = count / len(tickets) * 100
        print(f"  {status}: {count} ({pct:.1f}%)")


if __name__ == "__main__":
    main()
