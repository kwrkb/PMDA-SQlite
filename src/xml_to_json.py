"""
XML → JSON ロスレス変換

PMDA XMLファイルを機械的にJSONへ変換する。
全要素・属性・テキスト・tail・コメント・PIを保持し、情報の欠落を防ぐ。

1 XMLファイル → 1 JSONファイル (data/json/{source_dir}/{filename}.json)
"""

import json
import os
import sys
import time
from glob import glob
from lxml import etree

from config import JSON_DIR, get_xml_source_dir


def strip_namespace(tag: str) -> str:
    """名前空間URIを除去してローカル名を返す。

    例: '{http://...}PackIns' → 'PackIns'
    """
    if isinstance(tag, str) and tag.startswith('{'):
        return tag.split('}', 1)[1]
    return tag if isinstance(tag, str) else str(tag)


def element_to_dict(element) -> dict:
    """lxml要素を再帰的にdictへ変換する。

    保持する情報:
      - _tag: 要素名（名前空間除去済み）
      - _attrib: 属性辞書（存在する場合）
      - _text: 要素の直接テキスト（存在する場合）
      - _tail: 要素の後続テキスト（存在する場合）
      - _children: 子要素リスト（存在する場合）
      - _comment: コメントノード
      - _pi: Processing Instruction
    """
    # コメントノード
    if callable(element.tag):
        # lxmlではComment/PIのtagはcallable
        if element.tag is etree.Comment:
            return {"_comment": element.text or ""}
        if element.tag is etree.ProcessingInstruction:
            pi = {"target": element.target}
            if element.text:
                pi["text"] = element.text
            if element.tail and element.tail.strip():
                pi["_tail"] = element.tail.strip()
            return {"_pi": pi}
        return {}

    node = {"_tag": strip_namespace(element.tag)}

    # 属性（名前空間プレフィックスも除去）
    if element.attrib:
        attrib = {}
        for key, value in element.attrib.items():
            attrib[strip_namespace(key)] = value
        node["_attrib"] = attrib

    # テキスト
    if element.text and element.text.strip():
        node["_text"] = element.text.strip()
    elif element.text and '\n' not in element.text and element.text != element.text.strip():
        # 空白のみだがインデントではない場合（例: 半角スペース1個）
        pass

    # 子要素
    children = []
    for child in element:
        child_dict = element_to_dict(child)
        if child_dict:
            children.append(child_dict)
            # 子要素のtail（兄弟間テキスト）
            if child.tail and child.tail.strip():
                child_dict["_tail"] = child.tail.strip()

    if children:
        node["_children"] = children

    return node


def convert_xml_to_json(xml_path: str) -> dict:
    """1つのXMLファイルをパースしてdictに変換する。

    Args:
        xml_path: XMLファイルのパス

    Returns:
        変換されたdict
    """
    tree = etree.parse(xml_path)
    root = tree.getroot()
    return element_to_dict(root)


def convert_all(xml_source_dir: str, json_output_dir: str, limit: int = None):
    """XMLソースディレクトリ内の全XMLをJSONに変換する。

    Args:
        xml_source_dir: SGML_XML ディレクトリのパス
        json_output_dir: JSON出力先ディレクトリ
        limit: 処理するサブディレクトリ数の上限（Noneで全件）
    """
    subdirs = sorted([
        d for d in os.listdir(xml_source_dir)
        if os.path.isdir(os.path.join(xml_source_dir, d))
    ])

    total = len(subdirs)
    if limit:
        subdirs = subdirs[:limit]

    converted = 0
    errors = 0
    start_time = time.time()

    print(f"========================================")
    print(f"XML → JSON 変換開始")
    print(f"========================================")
    print(f"入力: {xml_source_dir}")
    print(f"出力: {json_output_dir}")
    print(f"対象ディレクトリ数: {total}")
    if limit:
        print(f"処理上限: {limit}")
    print()

    for i, subdir in enumerate(subdirs):
        xml_dir = os.path.join(xml_source_dir, subdir)
        xml_files = glob(os.path.join(xml_dir, "*.xml"))

        if not xml_files:
            continue

        # 出力ディレクトリ作成
        out_dir = os.path.join(json_output_dir, subdir)
        os.makedirs(out_dir, exist_ok=True)

        for xml_file in xml_files:
            basename = os.path.splitext(os.path.basename(xml_file))[0]
            json_path = os.path.join(out_dir, f"{basename}.json")

            try:
                data = convert_xml_to_json(xml_file)
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                converted += 1
            except Exception as e:
                print(f"  ERROR: {xml_file}: {e}")
                errors += 1

        # 進捗表示（500件ごと、または最後）
        if (i + 1) % 500 == 0 or i == len(subdirs) - 1:
            elapsed = time.time() - start_time
            print(f"  [{i+1}/{len(subdirs)}] 変換済: {converted}, エラー: {errors} ({elapsed:.1f}秒)")

    elapsed = time.time() - start_time

    print()
    print(f"========================================")
    print(f"変換完了")
    print(f"========================================")
    print(f"変換成功: {converted}件")
    print(f"エラー: {errors}件")
    print(f"所要時間: {elapsed:.1f}秒")

    return converted, errors


if __name__ == '__main__':
    limit = None
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            print("エラー: 引数は整数で指定してください")
            print("使用例: python3 src/xml_to_json.py 10")
            sys.exit(1)

    xml_source = get_xml_source_dir()
    if not xml_source:
        print("エラー: XMLソースディレクトリが見つかりません")
        sys.exit(1)

    convert_all(xml_source, JSON_DIR, limit=limit)
