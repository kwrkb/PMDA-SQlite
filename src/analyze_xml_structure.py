import os
import glob
import xml.etree.ElementTree as etree
from collections import Counter, defaultdict
import sys
import re

# 名前空間定義（既存コードより推測、必要に応じて調整）
NAMESPACES = {
    'p': 'http://info.pmda.go.jp/namespace/prescription_drugs/package_insert/1.0'
}

def get_local_name(tag):
    # {http://...}Tag -> Tag
    if '}' in tag:
        return tag.split('}', 1)[1]
    return tag

def analyze_xml_structure(file_paths):
    # 標準ETだと親参照ができないため、再帰関数で処理するラッパー
    return analyze_xml_structure_recursive(file_paths)

def analyze_xml_structure_recursive(file_paths):
    tag_counter = Counter()
    path_counter = Counter()
    text_content_sample = defaultdict(list)

    for i, file_path in enumerate(file_paths):
        if i % 100 == 0:
            print(f"Processing {i}/{len(file_paths)}: {file_path}")

        try:
            tree = etree.parse(file_path)
            root = tree.getroot()
            
            def traverse(element, path_stack):
                tag = get_local_name(element.tag)
                current_path = path_stack + [tag]
                path_str = "/" + "/".join(current_path)
                
                tag_counter[tag] += 1
                path_counter[path_str] += 1
                
                if element.text and element.text.strip():
                    if len(text_content_sample[path_str]) < 5:
                        text_content_sample[path_str].append(element.text.strip())
                
                for child in element:
                    traverse(child, current_path)

            traverse(root, [])

        except Exception as e:
            print(f"Error processing {file_path}: {e}")

    return tag_counter, path_counter, text_content_sample


def main():
    base_dir = "data/PMDAraw/pmda_all_20251122/SGML_XML/"
    # 全ファイルを取得
    all_files = glob.glob(os.path.join(base_dir, "**", "*.xml"), recursive=True)
    
    # ユーザー引数があれば制限する
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])
        files_to_process = all_files[:limit]
    else:
        files_to_process = all_files

    print(f"Total files found: {len(all_files)}")
    print(f"Analyzing {len(files_to_process)} files...")

    tag_counts, path_counts, samples = analyze_xml_structure(files_to_process)

    print("\n--- Top 50 Frequent Tags ---")
    for tag, count in tag_counts.most_common(50):
        print(f"{tag}: {count}")

    print("\n--- Top 100 Frequent Paths ---")
    for path, count in path_counts.most_common(100):
        print(f"{path}: {count}")
        if path in samples and samples[path]:
            print(f"  Sample: {samples[path][0][:50]}...")

if __name__ == "__main__":
    main()
