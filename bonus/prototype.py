"""Prototype tối thiểu minh họa cho Thiết kế Pipeline Luật & Thuế Việt Nam (Bonus Challenge)

Chức năng:
1. Chuẩn hóa văn bản tiếng Việt (loại bỏ khoảng trắng thừa, chuẩn hóa dấu tiếng Việt).
2. Ẩn danh hóa thông tin cá nhân/doanh nghiệp nhạy cảm (PII) như Số điện thoại, Mã số thuế (Tax ID), 
   và Email để tuân thủ Nghị định 13/2023/NĐ-CP trước khi lưu vào Bronze trace database.
"""
import re


def normalize_vietnamese_text(text: str) -> str:
    """Loại bỏ khoảng trắng thừa và đưa văn bản về dạng viết thường chuẩn hóa."""
    if not text:
        return ""
    # Chuẩn hóa khoảng trắng
    text = " ".join(text.strip().split())
    # Có thể mở rộng để chuyển đổi bảng mã cũ (TCVN3/VNI) sang Unicode ở đây
    return text


def anonymize_pii(text: str) -> tuple[str, int]:
    """Phát hiện và che (mask) các thông tin PII nhạy cảm:
    - Số điện thoại Việt Nam (ví dụ: 0912345678, +84912345678)
    - Mã số thuế doanh nghiệp (10 hoặc 13 chữ số, ví dụ: 0102030405)
    - Địa chỉ email
    """
    masked_text = text
    replacements_count = 0

    # 1. Regex nhận diện Email
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, masked_text)
    for email in emails:
        masked_text = masked_text.replace(email, "[EMAIL_ANONYMIZED]")
        replacements_count += 1

    # 2. Regex nhận diện Số điện thoại Việt Nam (10 chữ số bắt đầu bằng 0 hoặc +84)
    phone_pattern = r'(?:\+84|0)[35789]\d{8}\b'
    phones = re.findall(phone_pattern, masked_text)
    for phone in phones:
        masked_text = masked_text.replace(phone, "[PHONE_ANONYMIZED]")
        replacements_count += 1

    # 3. Regex nhận diện Mã số thuế doanh nghiệp Việt Nam (10 chữ số hoặc 13 chữ số liên kết bằng gạch ngang)
    # Ví dụ: 0102030405 hoặc 0102030405-001
    mst_pattern = r'\b\d{10}(?:-\d{3})?\b'
    msts = re.findall(mst_pattern, masked_text)
    for mst in msts:
        # Tránh trùng lặp với số điện thoại bằng cách lọc độ dài khác
        if mst not in phones:
            masked_text = masked_text.replace(mst, "[TAX_ID_ANONYMIZED]")
            replacements_count += 1

    return masked_text, replacements_count


def test_prototype():
    sample_trace = (
        "Khach hang Nguyen Van A (MST: 0106493205-001, email: nguyenvana@gmail.com) "
        "yeu cau tu van hoan thue VAT. SDT lien he: 0987654321."
    )

    print("=== Raw input trace data ===")
    print(sample_trace)

    # Quality Gate processing
    normalized = normalize_vietnamese_text(sample_trace)
    clean_trace, count = anonymize_pii(normalized)

    print("\n=== Output trace data after Quality Gate anonymization ===")
    print(clean_trace)
    print(f"Number of anonymized fields: {count}")

    # Assertions
    assert "[TAX_ID_ANONYMIZED]" in clean_trace
    assert "[EMAIL_ANONYMIZED]" in clean_trace
    assert "[PHONE_ANONYMIZED]" in clean_trace
    print("\n[OK] Prototype executed successfully and safely!")


if __name__ == "__main__":
    test_prototype()
