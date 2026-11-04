import re
from .text_normalizer import normalize_description

CATEGORY_KEYWORDS = {
    "Refunds": ["purchase return", "order refund", "refund received", "refund credit", "refund amazon", "amazon refund", "refund order", "cashback received", "cashback", "refund", "reversal"],
    "Salary": ["salary credit", "salary transfer", "salary advance", "payroll", "monthly salary", "wages credit", "bonus credit"],
    "Food & Dining": ["swiggy", "zomato", "foodpanda", "dominos", "pizza hut", "kfc", "mcdonalds", "subway", "starbucks", "cafe coffee day", "tea trail", "restaurant", "food"],
    "Groceries": ["dmart", "vishal mega mart", "bigbasket", "blinkit", "jiomart", "reliance smart", "more supermarket", "natures basket", "supermarket", "kirana", "grocery", "vegetable market"],
    "Transportation": ["uber", "ola", "rapido", "redbus", "gsrtc", "metro", "bus ticket", "city bus", "auto rickshaw", "railway local", "cab fare", "taxi service", "public transport", "smart card"],
    "Utilities": ["adani electricity", "torrent power", "bescom", "msedcl", "airtel broadband", "jio postpaid", "gujarat gas", "tata play", "mobile postpaid", "broadband", "electricity", "utility", "water bill", "municipal water", "gas connection", "telephone landline"],
    "Shopping": ["amazon", "flipkart", "myntra", "ajio", "nykaa", "croma", "reliance digital", "westside", "shoppers stop", "meesho", "paytm mall", "decathlon", "online store", "shopping", "retail"],
    "Fuel": ["indian oil", "iocl", "hp petrol", "hpcl", "bpcl", "nayara", "shell", "petrol pump", "fuel", "cng"],
    "Healthcare": ["medplus", "apollo pharmacy", "netmeds", "1mg", "pathology lab", "mri scan", "doctor appointment", "hospital", "clinic", "pharmacy", "diagnostic centre", "medical"],
    "Entertainment": ["netflix", "spotify", "bookmyshow", "pvr", "cinepolis", "hotstar", "sonyliv", "youtube premium", "zee5", "steam games", "playstation", "music streaming", "event ticket", "cinema", "movie"],
    "Education": ["university fee", "college fee", "school fee", "school fees", "tuition fee", "examination fee", "nirma university", "coursera", "udemy", "online learning", "coaching class", "admission fee", "certification exam", "student portal", "hostel fee", "education"],
    "Rent": ["house rent", "flat rent", "room rent", "monthly rent", "landlord rent", "rent transfer", "rental payment", "house lease", "rent"],
    "Insurance": ["lic", "hdfc life", "star health", "icici prudential", "bajaj allianz", "term life", "health policy", "policy premium", "life cover", "insurance premium", "insurance"],
    "EMI & Loan Payments": ["bajaj finance", "loan emi", "home loan", "personal loan", "car loan", "auto loan", "credit loan", "loan account", "nach emi", "loan repayment", "installment", "emi"],
    "Investments": ["mutual fund", "sip", "zerodha", "demat", "nps", "ppf", "stock broker", "broking fund", "recurring deposit", "gold etf", "investment"],
    "Bank Charges": ["sms alert fee", "service charge", "account maintenance", "minimum balance penalty", "atm decline charge", "neft fee", "bank charge", "annual fee"],
    "ATM Withdrawal": ["atm cash", "cash withdrawal", "atm wdl", "cash dispense", "atm failed"],
    "Money Transfer": ["upi sent", "upi received", "self transfer"],
    "Travel": ["air india", "indigo", "irctc", "make my trip", "goibibo", "oyo", "hotel booking", "hotel stay", "hotel payment", "international hotel", "railway tatkal", "flight booking", "holiday package", "airport lounge", "yatra", "airlines", "travel"],
}

GENERIC_KEYWORDS = {"food", "grocery", "retail", "shopping", "transfer", "travel", "medical", "insurance", "education", "utility", "rent", "fuel", "refund", "reversal", "cashback"}


def classify_rule(description: str):
    text = normalize_description(description)
    matches = []
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            pattern = rf"\b{re.escape(normalize_description(keyword))}\b"
            if re.search(pattern, text):
                normalized_keyword = normalize_description(keyword)
                matches.append((category, len(normalized_keyword), normalized_keyword not in GENERIC_KEYWORDS))
    if matches:
        category = max(matches, key=lambda match: (match[2], match[1]))[0]
        return category, 0.92
    return None, 0.0
