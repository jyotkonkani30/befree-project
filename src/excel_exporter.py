from io import BytesIO
import pandas as pd
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter
from .transaction_output import prepare_transaction_output


def export_excel(frame: pd.DataFrame, account=None) -> bytes:
    output = BytesIO()
    clean_frame = prepare_transaction_output(frame)
    excel_frame = clean_frame.copy()
    excel_frame["Transaction Date"] = pd.to_datetime(
        excel_frame["Transaction Date"], format="%d-%m-%Y", errors="coerce"
    )
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        excel_frame.to_excel(writer, index=False, sheet_name="Transactions")
        workbook = writer.book
        for sheet in workbook.worksheets:
            sheet.freeze_panes = "A2"
            sheet.auto_filter.ref = sheet.dimensions
            for cell in sheet[1]:
                cell.font = Font(bold=True)
            for cell in sheet["A"][1:]:
                cell.number_format = "DD-MM-YYYY"
            for column_name in ("Debit", "Credit", "Balance"):
                column_index = list(clean_frame.columns).index(column_name) + 1
                for cell in list(sheet.columns)[column_index - 1][1:]:
                    cell.number_format = '#,##0.00'
            for column in sheet.columns:
                width = min(max(len(str(cell.value or "")) for cell in column) + 2, 45)
                sheet.column_dimensions[get_column_letter(column[0].column)].width = width
    return output.getvalue()
