"""Parses the MoMo SMS backup XML (data/raw/modified_sms_v2.xml) into a flat
list of transaction dicts, ready to serialize as JSON for the REST API.

Usage:
    python -m dsa.parse_sms
    python -m dsa.parse_sms --xml path/to/file.xml --out data/processed/transactions.json
"""

from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

DEFAULT_XML_PATH = Path("data/raw/modified_sms_v2.xml")
DEFAULT_JSON_PATH = Path("data/processed/transactions.json")

OTP_MARKER = "one-time password"


def _parse_amount(raw: str | None) -> float | None:
    if raw is None:
        return None
    raw = raw.strip().replace(",", "")
    return float(raw) if raw else None


def _epoch_ms_to_iso(ms: str) -> str:
    return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).isoformat()


def _body_date_to_iso(raw: str | None) -> str | None:
    if not raw:
        return None
    return datetime.strptime(raw, "%Y-%m-%d %H:%M:%S").isoformat()


# Each entry: (type_name, compiled regex, extractor(match) -> dict of fields).
# Order matters — more specific patterns (e.g. the *162*/*143* prefixed ones)
# are tried before anything that could loosely overlap.
_PATTERNS: list[tuple[str, re.Pattern, Callable[[re.Match], dict[str, Any]]]] = [
    ("BANK_DEPOSIT", re.compile(
        r"^\*113\*R\*A bank deposit of ([\d,]+) RWF has been added to your mobile money account at ([\d-]+ [\d:]+)\. "
        r"Your NEW BALANCE :([\d,]+) RWF\. Cash Deposit::CASH::::0::(\d+)"),
     lambda m: {"amount": _parse_amount(m.group(1)), "transaction_datetime": _body_date_to_iso(m.group(2)),
                "balance_after": _parse_amount(m.group(3)), "sender": {"name": None, "phone": m.group(4)},
                "receiver": None, "direction": "CREDIT", "fee": 0.0, "transaction_id": None}),

    ("PAYMENT_MERCHANT_CODE", re.compile(
        r"^TxId: (\d+)\. Your payment of ([\d,]+) RWF to (.+?) (\d+) has been completed at ([\d-]+ [\d:]+)\. "
        r"Your new balance: ([\d,]+) RWF\. Fee was ([\d,]+) RWF"),
     lambda m: {"transaction_id": m.group(1), "amount": _parse_amount(m.group(2)),
                "receiver": {"name": m.group(3).strip(), "phone": None, "merchant_code": m.group(4)},
                "sender": None, "transaction_datetime": _body_date_to_iso(m.group(5)),
                "balance_after": _parse_amount(m.group(6)), "fee": _parse_amount(m.group(7)), "direction": "DEBIT"}),

    ("TRANSFER_MOBILE", re.compile(
        r"^\*165\*S\*([\d,]+) RWF transferred to (.+?) \((\d+)\) from (\d+) at ([\d-]+ [\d:]+) \. "
        r"Fee was: ([\d,]+) RWF\. New balance: ([\d,]+) RWF"),
     lambda m: {"amount": _parse_amount(m.group(1)), "receiver": {"name": m.group(2).strip(), "phone": m.group(3)},
                "sender": {"name": None, "phone": None, "account": m.group(4)},
                "transaction_datetime": _body_date_to_iso(m.group(5)), "fee": _parse_amount(m.group(6)),
                "balance_after": _parse_amount(m.group(7)), "direction": "DEBIT", "transaction_id": None}),

    ("AIRTIME_BUNDLE_PAYMENT", re.compile(
        r"^\*162\*TxId:(\d+)\*S\*Your payment of ([\d,]+) RWF to (.+?) with token\s*(\S*)\s*has been completed at ([\d-]+ [\d:]+)\. "
        r"Fee was ([\d,]+) RWF\. Your new balance: ([\d,]+) RWF\s*\. Message:\s*(.*?)\.\s*\*EN#"),
     lambda m: {"transaction_id": m.group(1), "amount": _parse_amount(m.group(2)),
                "receiver": {"name": m.group(3).strip(), "phone": None, "token": m.group(4) or None},
                "sender": None, "transaction_datetime": _body_date_to_iso(m.group(5)), "fee": _parse_amount(m.group(6)),
                "balance_after": _parse_amount(m.group(7)), "direction": "DEBIT"}),

    ("THIRD_PARTY_TXN", re.compile(
        r"^\*164\*S\*Y'ello,A transaction of ([\d,]+) RWF by (.+?) on your MOMO account was successfully completed at ([\d-]+ [\d:]+)\. "
        r"Message from debit receiver:\s*(.*?)\.\s*Your new balance:([\d,]*)\s*RWF\.\s*Fee was ([\d,]+) RWF\. "
        r"Financial Transaction Id: (\d+)\.(?:\s*External Transaction Id: (\d+)\.)?"),
     lambda m: {"amount": _parse_amount(m.group(1)), "receiver": {"name": m.group(2).strip(), "phone": None},
                "sender": None, "transaction_datetime": _body_date_to_iso(m.group(3)), "fee": _parse_amount(m.group(6)),
                "balance_after": _parse_amount(m.group(5)), "direction": "DEBIT",
                "transaction_id": m.group(7), "external_transaction_id": m.group(8)}),

    ("RECEIVE_MONEY", re.compile(
        r"^You have received ([\d,]+) RWF from (.+?) \(([\d*]+)\) on your mobile money account at ([\d-]+ [\d:]+)\. "
        r"Message from sender:\s*(.*?)\.\s*Your new balance:([\d,]+) RWF\. Financial Transaction Id: (\d+)\."),
     lambda m: {"amount": _parse_amount(m.group(1)), "sender": {"name": m.group(2).strip(), "phone": m.group(3)},
                "receiver": None, "transaction_datetime": _body_date_to_iso(m.group(4)),
                "balance_after": _parse_amount(m.group(6)), "direction": "CREDIT",
                "transaction_id": m.group(7), "fee": 0.0}),

    ("AGENT_WITHDRAWAL", re.compile(
        r"^You (.+?) \(([\d*]+)\) have via agent: Agent (.+?) \((\d+)\), withdrawn ([\d,]+) RWF from your mobile money account: (\d+) "
        r"at ([\d-]+ [\d:]+) and you can now collect your money in cash\. Your new balance: ([\d,]+) RWF\. "
        r"Fee paid: ([\d,]+) RWF\. Message from agent:\s*(.*?)\.\s*Financial Transaction Id: (\d+)\."),
     lambda m: {"amount": _parse_amount(m.group(5)),
                "sender": {"name": m.group(1).strip(), "phone": m.group(2), "account": m.group(6)},
                "receiver": {"name": "Agent " + m.group(3).strip(), "phone": m.group(4), "role": "AGENT"},
                "transaction_datetime": _body_date_to_iso(m.group(7)), "balance_after": _parse_amount(m.group(8)),
                "fee": _parse_amount(m.group(9)), "direction": "DEBIT", "transaction_id": m.group(11)}),

    ("REVERSAL_COMPLETED", re.compile(
        r"^\*143\*S\*Your transaction to (.+?) \((\d+)\) with ([\d,]+) RWF has been reversed at ([\d-]+ [\d:]+)\. "
        r"Your new balance is ([\d,]+) RWF"),
     lambda m: {"amount": _parse_amount(m.group(3)), "receiver": {"name": m.group(1).strip(), "phone": m.group(2)},
                "sender": None, "transaction_datetime": _body_date_to_iso(m.group(4)),
                "balance_after": _parse_amount(m.group(5)), "direction": "CREDIT",
                "transaction_id": None, "fee": 0.0}),

    ("REVERSAL_INITIATED", re.compile(
        r"^A reversal has been initiated for your transaction to (.+?) \((\d+)\) with ([\d,]+) RWF\."),
     lambda m: {"amount": _parse_amount(m.group(3)), "receiver": {"name": m.group(1).strip(), "phone": m.group(2)},
                "sender": None, "transaction_datetime": None, "balance_after": None,
                "direction": None, "transaction_id": None, "fee": 0.0}),

    ("FAILED_TOKEN_PAYMENT", re.compile(
        r"^\*143\*TxId:(\d+)\*S\*Your payment of ([\d,]+) RWF to (.+?) with token\s*(\S*)\s*has failed at ([\d-]+ [\d:]+)\. "
        r"Message:\s*(.*?)\.\s*\*EN#"),
     lambda m: {"transaction_id": m.group(1), "amount": _parse_amount(m.group(2)),
                "receiver": {"name": m.group(3).strip(), "phone": None}, "sender": None,
                "transaction_datetime": _body_date_to_iso(m.group(5)), "balance_after": None,
                "fee": None, "direction": "DEBIT"}),

    ("FAILED_GENERIC", re.compile(
        r"^\*143\*R\*Y'ello, the transaction with amount ([\d,]+) RWF for (.+?) with message:\s*(.*?)\s*failed at ([\d-]+ [\d:]+)"),
     lambda m: {"amount": _parse_amount(m.group(1)), "receiver": {"name": m.group(2).strip(), "phone": None},
                "sender": None, "transaction_datetime": _body_date_to_iso(m.group(4)), "balance_after": None,
                "direction": "DEBIT", "transaction_id": None, "fee": None}),

    ("BANK_TRANSFER_OUT", re.compile(
        r"^You have transferred ([\d,]+) RWF to (.+?) \((\d+)\) from your mobile money account (\S+) imbank\.bank at ([\d-]+ [\d:]+)\. "
        r"Your new balance:\s*(.*?)\s*\. Message from sender:\s*(.*?)\.\s*Message to receiver:\s*(.*?)\.\s*Financial Transaction Id: (\d+)\."),
     lambda m: {"amount": _parse_amount(m.group(1)), "receiver": {"name": m.group(2).strip(), "phone": m.group(3)},
                "sender": {"name": None, "phone": None, "account": m.group(4)},
                "transaction_datetime": _body_date_to_iso(m.group(5)), "balance_after": _parse_amount(m.group(6)),
                "direction": "DEBIT", "transaction_id": m.group(9), "fee": None}),

    ("MERCHANT_PAYMENT_DISCOUNT", re.compile(
        r"^Your payment of ([\d,]+) RWF to (.+?) \((\d+)\) has been completed at ([\d-]+ [\d:]+)\. "
        r"Message:\s*(.*?)\.\s*Your new balance: ([\d,]+) RWF\. Fee was ([\d,]+) RWF\. "
        r"The amount was subject to a discount of ([\d,]+) RWF and coupons worth\s*(.*?)\.\s*Financial Transaction Id: (\d+)\."),
     lambda m: {"amount": _parse_amount(m.group(1)), "receiver": {"name": m.group(2).strip(), "phone": m.group(3)},
                "sender": None, "transaction_datetime": _body_date_to_iso(m.group(4)),
                "balance_after": _parse_amount(m.group(6)), "fee": _parse_amount(m.group(7)),
                "direction": "DEBIT", "transaction_id": m.group(10), "discount": _parse_amount(m.group(8))}),

    ("BUNDLE_PURCHASE_USSD", re.compile(r"^Yello!Umaze kugura.*?igura ([\d,]+) RWF"),
     lambda m: {"amount": _parse_amount(m.group(1)), "sender": None, "receiver": None,
                "transaction_datetime": None, "balance_after": None, "direction": "DEBIT",
                "transaction_id": None, "fee": None}),
]


def parse_file(xml_path: Path | str) -> dict[str, Any]:
    """Parses the SMS backup XML into transactions + a dead-letter list.

    Returns {"transactions": [...], "dead_letter": [...], "non_transactional": [...], "stats": {...}}.
    Every <sms> element is accounted for in exactly one of the three lists.
    """
    tree = ET.parse(xml_path)
    transactions: list[dict[str, Any]] = []
    dead_letter: list[dict[str, Any]] = []
    non_transactional: list[dict[str, Any]] = []
    stats: dict[str, int] = {}

    for sms_id, sms in enumerate(tree.getroot().findall("sms"), start=1):
        body = sms.get("body", "") or ""
        sms_timestamp = _epoch_ms_to_iso(sms.get("date"))

        if OTP_MARKER in body:
            non_transactional.append({"id": sms_id, "type": "OTP", "sms_timestamp": sms_timestamp, "raw_body": body})
            stats["OTP"] = stats.get("OTP", 0) + 1
            continue

        for type_name, pattern, extract in _PATTERNS:
            match = pattern.search(body)
            if not match:
                continue
            record = {"id": sms_id, "type": type_name, "sms_timestamp": sms_timestamp, "raw_body": body}
            record.update(extract(match))
            transactions.append(record)
            stats[type_name] = stats.get(type_name, 0) + 1
            break
        else:
            dead_letter.append({"id": sms_id, "sms_timestamp": sms_timestamp, "raw_body": body})

    return {
        "transactions": transactions,
        "dead_letter": dead_letter,
        "non_transactional": non_transactional,
        "stats": stats,
    }


def to_json(result: dict[str, Any], out_path: Path | str) -> None:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result["transactions"], indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xml", type=Path, default=DEFAULT_XML_PATH)
    parser.add_argument("--out", type=Path, default=DEFAULT_JSON_PATH)
    args = parser.parse_args()

    result = parse_file(args.xml)
    total = len(result["transactions"]) + len(result["dead_letter"]) + len(result["non_transactional"])
    print(f"Parsed {len(result['transactions'])}/{total} records into transactions "
          f"({len(result['non_transactional'])} non-transactional OTP messages excluded, "
          f"{len(result['dead_letter'])} unmatched -> dead-letter).")
    print("By type:", json.dumps(result["stats"], indent=2))

    to_json(result, args.out)
    print(f"Wrote {args.out}")

    if result["dead_letter"]:
        dead_letter_path = args.out.parent / "dead_letter_sms.json"
        dead_letter_path.write_text(json.dumps(result["dead_letter"], indent=2), encoding="utf-8")
        print(f"Wrote {dead_letter_path}")


if __name__ == "__main__":
    main()
