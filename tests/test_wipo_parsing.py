from app.services.wipo import parse_wipo_html


def long_page(html: str) -> str:
    return html.replace("</body>", f"<p>{'页面正文 ' * 80}</p></body>")


def test_parse_membership_page_with_code_footnote_and_counts():
    html = long_page("""
    <html><body>
      <p>2026年5月19日状态</p>
      <table>
        <tr><th>双字母代码</th><th>成员国/成员</th><th>专利合作条约 (2)</th><th>巴黎公约 (2)</th><th>世界贸易组织 2 (2)</th></tr>
        <tr><td>AA</td><td>甲国</td><td>X</td><td>X</td><td>X</td></tr>
        <tr><td>BB 1</td><td>乙国 1</td><td>X</td><td>X</td><td>X</td></tr>
      </table>
      <p>1. 特殊说明。</p>
    </body></html>
    """)

    parsed = parse_wipo_html("wipo_pct_paris_wto_membership", html)

    assert parsed["is_valid"] is True
    assert parsed["source_status_date"] == "2026-05-19"
    assert parsed["records"] == [
        {
            "country_code": "AA",
            "name_zh": "甲国",
            "name_en": None,
            "data_type": "country",
            "is_pct_member": True,
            "is_paris_member": True,
            "source_url": "https://www.wipo.int/zh/web/pct-system/paris_wto_pct",
            "note": None,
            "raw": "AA | 甲国 | X | X",
        },
        {
            "country_code": "BB",
            "name_zh": "乙国",
            "name_en": None,
            "data_type": "country",
            "is_pct_member": True,
            "is_paris_member": True,
            "source_url": "https://www.wipo.int/zh/web/pct-system/paris_wto_pct",
            "note": "1. 特殊说明。",
            "raw": "BB 1 | 乙国 1 | X | X",
        },
    ]


def test_parse_time_limits_chapter_1_four_column_layout_and_no_false_status_date():
    html = long_page("""
    <html><body>
      <table>
        <tr><th>指定局/选定局</th><th>第I章 (根据 PCT条约第22条 )</th><th>第II章 (根据 PCT条约第39(1)条 )</th></tr>
        <tr><td>AP</td><td>非洲地区知识产权组织 4</td><td>31</td><td>31</td></tr>
        <tr><td>US</td><td>美利坚合众国</td><td>30</td><td>30</td></tr>
      </table>
      <p>2002-04-01 是脚注中的法律日期，不是来源状态日期。</p>
    </body></html>
    """)

    parsed = parse_wipo_html("wipo_pct_time_limits", html)

    assert parsed["is_valid"] is True
    assert parsed["source_status_date"] is None
    assert parsed["records"][0]["country_code"] == "AP"
    assert parsed["records"][0]["data_type"] == "regional_office"
    assert parsed["records"][0]["pct_entry_deadline_first_chapter"] == 31
    assert parsed["records"][1]["country_code"] == "US"
    assert parsed["records"][1]["data_type"] == "country"
    assert parsed["records"][1]["pct_entry_deadline_first_chapter"] == 30
