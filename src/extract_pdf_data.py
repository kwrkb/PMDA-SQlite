import subprocess
import json
import os

def extract_data_with_yomitoku(pdf_path, output_dir):
    """
    yomitokuを使ってPDFから情報を抽出し、JSONファイルとして保存します。
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 出力ファイル名を作成 (元のPDFファイル名から拡張子を除き、.jsonを付加)
    base_name = os.path.basename(pdf_path)
    file_name_without_ext = os.path.splitext(base_name)[0]
    output_json_path = os.path.join(output_dir, f"{file_name_without_ext}.json")

    # yomitoku コマンドの構築
    command = [
        "yomitoku",
        pdf_path,
        "-f", "json",
        "-o", output_dir,
        "--combine" # 全ページを1つのJSONファイルにまとめる
    ]

    print(f"yomitokuコマンドを実行中: {' '.join(command)}")
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        print("yomitoku実行成功。")
        if result.stdout:
            print("yomitoku stdout:")
            print(result.stdout)
        if result.stderr:
            print("yomitoku stderr:")
            print(result.stderr)
        
        # yomitokuはPDFを処理する際、PDF_<元のファイル名>.json という形式で出力する
        output_json_path = os.path.join(output_dir, f"PDF_{file_name_without_ext}.json")
        if os.path.exists(output_json_path):
            return output_json_path
        else:
            print(f"エラー: 期待されたJSONファイルが見つかりません: {output_json_path}")
            return None
    except subprocess.CalledProcessError as e:
        print(f"yomitoku実行中にエラーが発生しました: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return None

if __name__ == '__main__':
    pdf_file = "data/PMDAraw/pmda_all_20251122/PDF/氷酢酸.pdf"
    output_dir = "data/output"

    # .venv/bin/activate を実行して仮想環境をアクティベートしてからこのスクリプトを実行してください
    # 例: source .venv/bin/activate && python src/extract_pdf_data.py
    
    extracted_json_path = extract_data_with_yomitoku(pdf_file, output_dir)
    if extracted_json_path:
        print(f"抽出されたJSONファイル: {extracted_json_path}")
        # 抽出されたJSONファイルの内容を読み込んで表示
        try:
            with open(extracted_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # ファイルが大きすぎる場合は一部のみ表示
                if len(json.dumps(data)) > 2000:
                    print(json.dumps(data, indent=2)[:2000] + "...\n(出力が長すぎるため一部のみ表示)")
                else:
                    print(json.dumps(data, indent=2))
        except Exception as e:
            print(f"JSONファイルの読み込み中にエラーが発生しました: {e}")
    else:
        print("PDFからのデータ抽出に失敗しました。")
