/*****************************/		
/* XMLスタイルシート適用手順 */		
/*****************************/		
			
①確認するXMLを、styles配下に格納します。		
  ★部分参照		
  =========================================		
    styles		
    ┣ css		
    ┣ include		
★  ┣ xxxxxxxxxxxxxxxxxxxxx.xml		
    ┗ js		
  =========================================		
	  		
②確認するXMLの冒頭部分に以下の行を追加します。		
  ★部分参照		
  =============================================================================================================================================		
  <?xml version="1.0" encoding="utf-8"?>		
★<?xml-stylesheet type="text/xsl" href="preview_ja.xsl" ?>		
  <PackIns version="1.0" xmlKind="Packins" drugType="Medicine" xmlns="http://info.pmda.go.jp/namespace/prescription_drugs/package_insert/1.0">		
  =============================================================================================================================================		
			
③スタイルは、Microsoft Edgeの「Internet Explorerモード」等で確認することができます。
  「Internet Explorerモード」を有効にするには、次の手順を参考にしてください。
    1. Microsoft Edgeのアドレスバーに「edge://settings/defaultbrowser」と入力します。
    2. 「Internet Explorerでの再読み込みをサイトに許可する」をスライドして、[許可] に切り替えます。
    3. Microsoft Edgeを再起動します。
  「Internet Explorerモード」有効後のMicrosoft EdgeでXMLを表示する手順は、以下のとおりです。
    1. スタイルを確認するXMLをMicrosoft Edgeで開きます。
    2. ウィンドウの右上隅にある […] をクリックします。
    3. [Internet Explorer モードで再読み込みする] を選択します。
       Microsoft Edgeバージョン92 以前を使用している場合は、[その他のツール] > [Internet Explorer モードの再読み込み] を選択します。	
			
			
※英語版を参照したい場合		

②-1 確認するXMLの冒頭部分に以下の行を追加します。		
  ★部分参照		
  =============================================================================================================================================		
  <?xml version="1.0" encoding="utf-8"?>		
★<?xml-stylesheet type="text/xsl" href="preview_en.xsl" ?>		
  <PackIns version="1.0" xmlKind="Packins" drugType="Medicine" xmlns="http://info.pmda.go.jp/namespace/prescription_drugs/package_insert/1.0">		
  =============================================================================================================================================		
			
②-2 lang.xslを編集し保存します。		
  ★部分参照		
  ==============================================================		
  <?xml version="1.0" encoding="UTF-8" ?>		
  <xsl:stylesheet version="1.0"		
  	  xmlns:xsl="http://www.w3.org/1999/XSL/Transform">	
★	  <xsl:variable name="lang">en</xsl:variable>	
  </xsl:stylesheet>		
  ==============================================================		
  ※ ja → en に変更します。		
			
③同上		
