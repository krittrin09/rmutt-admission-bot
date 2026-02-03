def debug_text_lines(clean_text: str) -> list[str]:
    lines = [l.strip() for l in clean_text.split("\n") if l.strip()]

    def split_multi_fields(line, fields):
        out = []
        for field in fields:
            if field in line:
                start = line.index(field) + len(field)
                end = len(line)
                for other in fields:
                    if other != field and other in line[start:]:
                        pos = line.index(other, start)
                        end = min(end, pos)
                value = line[start:end].strip()
                out.append(f"{field} {value}")
        return out

    new_lines = []
    for l in lines:
        if "เพศ" in l and "สัญชาติ" in l and "ศาสนา" in l:
            new_lines.extend(split_multi_fields(l, ["เพศ", "สัญชาติ", "ศาสนา"]))
        else:
            new_lines.append(l)

    return new_lines
