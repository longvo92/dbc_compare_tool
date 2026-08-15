# CLAUDE.md

Repo: `dbc-compare-tool`. So sánh hai thư mục baseline CAN DBC, xuất Excel change report.

Luật ở đây thắng `~/.claude/CLAUDE.md` khi mâu thuẫn.

## Ràng buộc

- **`requires-python = ">=3.9"`.** CI chạy 3.9, 3.10, 3.12 trên Linux + Windows. Vì hỗ trợ 3.9: mọi module/test phải có `from __future__ import annotations`; **không** dùng `match`, **không** dùng `X | Y` ở runtime (chỉ trong annotation, để future-import biến thành string). `list[str]`/`dict[...]` subscription thì 3.9 chịu được.
- Dependency cứng, không cần hỏi: `cantools>=40.3.0`, `openpyxl>=3.1.0`, `PySide6>=6.7.0`. Thêm dependency **mới** ngoài danh sách này thì nói lý do trước.
- **`PySide6` chỉ được import trong `ui/`.** CI cố tình không cài PySide6 — engine và report phải chạy được khi thiếu Qt. Import Qt ở `core/` hoặc `report/` là làm vỡ CI.
- Layout `src/` (setuptools `packages.find where = ["src"]`). Code mới đặt trong `src/dbc_compare_tool/`.

## Layout

```
src/dbc_compare_tool/
├── cli.py           # CLI entry
├── __main__.py
├── core/
│   ├── discovery.py   # tìm & ghép cặp file DBC giữa hai baseline
│   ├── parser.py      # đọc DBC qua cantools
│   ├── models.py      # data model
│   ├── comparator.py  # engine so sánh, lọc theo change type
│   └── rename.py      # heuristic phát hiện rename (scoring + weights)
├── report/excel.py    # openpyxl
└── ui/main_window.py  # PySide6
```

Nguyên tắc đã chốt: **lọc/nghiệp vụ nằm ở engine, không nằm ở UI.** UI chỉ dựng view và gọi `core`. Đã refactor một lần để đưa change-type filtering từ UI về engine — đừng đẩy ngược lại.

## Chạy & test

```bash
python -m dbc_compare_tool.cli --old examples/old --new examples/new --out report.xlsx
python -m unittest discover -s tests -v      # KHÔNG phải pytest
python scripts/build.py                       # đóng gói
run_gui.bat / run_cli.bat                     # tiện chạy trên Windows
```

Smoke test của CI là chạy CLI trên `examples/old` vs `examples/new` — chạy lại lệnh đó sau khi sửa engine.

## Docs

Repo public. Đổi hành vi → cập nhật `README.md`, `docs/architecture.md`, và `resources/help/release_notes.md` (link Changelog trong metadata trỏ vào đó) trong cùng change, tiếng Anh.

Đổi tiêu chí/trọng số rename → cập nhật phần mô tả scoring trong docs, vì nó đã được document ra ngoài.

## Ghi chú

`AGENTS.md` cũ đã bỏ. Mức tự chủ theo global: cứ làm, thiếu thông tin thì hỏi một câu — không tự nới scope thành "own the project end-to-end".
