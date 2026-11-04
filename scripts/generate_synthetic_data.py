from pathlib import Path
import random
import pandas as pd

CATEGORIES = {
    "Salary": ["SALARY CREDIT", "PAYROLL CREDIT", "MONTHLY WAGES"],
    "Food & Dining": ["UPI SWIGGY ORDER", "ZOMATO FOOD", "RESTAURANT PAYMENT"],
    "Shopping": ["AMAZON PURCHASE", "FLIPKART ORDER", "MYNTRA SHOPPING"],
    "Groceries": ["DMART GROCERY", "BIGBASKET ORDER", "GROCERY STORE"],
    "Transportation": ["UBER RIDE", "OLA CAB", "METRO CARD"],
    "Fuel": ["INDIAN OIL PETROL", "HPCL FUEL", "BPCL FUEL"],
    "Rent": ["HOUSE RENT", "MONTHLY RENT"],
    "Utilities": ["ELECTRICITY BILL", "WATER BILL", "GAS BILL"],
    "Healthcare": ["APOLLO PHARMACY", "HOSPITAL PAYMENT", "MEDICAL STORE"],
    "Education": ["SCHOOL FEES", "COLLEGE TUITION", "ONLINE COURSE"],
    "Entertainment": ["NETFLIX SUBSCRIPTION", "SPOTIFY PREMIUM", "CINEMA TICKET"],
    "Travel": ["AIRLINES BOOKING", "HOTEL BOOKING", "MAKEMYTRIP TRAVEL"],
    "EMI & Loan Payments": ["HOME LOAN EMI", "CAR LOAN EMI", "PERSONAL LOAN"],
    "Insurance": ["LIC PREMIUM", "HEALTH INSURANCE", "INSURANCE PAYMENT"],
    "Investments": ["MUTUAL FUND SIP", "ZERODHA INVESTMENT", "EQUITY SIP"],
    "ATM Withdrawal": ["ATM WDL CASH", "CASH WITHDRAWAL"],
    "Bank Charges": ["BANK SERVICE CHARGE", "ANNUAL FEE", "BANK CHARGE"],
    "Money Transfer": ["NEFT TRANSFER", "IMPS TRANSFER", "UPI TRANSFER"],
    "Refunds": ["AMAZON REFUND", "PAYMENT REVERSAL", "CASHBACK REFUND"],
    "Other / Unclassified": ["MISC PAYMENT", "UNKNOWN MERCHANT", "GENERAL TRANSFER"],
}


def generate_dataset(path="data/synthetic_transactions.csv", count=2000):
    random.seed(42)
    rows = []
    date = pd.Timestamp("2024-01-01")
    for index in range(count):
        category = list(CATEGORIES)[index % len(CATEGORIES)]
        description = random.choice(CATEGORIES[category]) + f" REF{index:05d}"
        amount = round(random.uniform(50, 50000), 2)
        credit = category == "Salary" or category == "Refunds" or (category == "Money Transfer" and index % 2 == 0)
        rows.append({"date": (date + pd.Timedelta(days=index % 365)).date().isoformat(), "description": description,
                     "debit": None if credit else amount, "credit": amount if credit else None, "balance": 100000 + index, "category": category})
    output = Path(path); output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output, index=False)
    return output


if __name__ == "__main__":
    generate_dataset()
