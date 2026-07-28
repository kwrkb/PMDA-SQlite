<?xml version="1.0" encoding="UTF-8" ?> 
<!-- XSLTスタイルシート宣言--> 
<xsl:stylesheet version="1.0" 
	xmlns:ns="http://info.pmda.go.jp/namespace/prescription_drugs/package_insert/1.0" 
	xmlns:xsl="http://www.w3.org/1999/XSL/Transform"> 
<!-- 出力形式 --> 
<xsl:output method="html" doctype-system="about:legacy-compat" encoding="UTF-8" /> 
<!-- 言語設定 --> 
<xsl:variable name="lang">ja</xsl:variable> 
<xsl:variable name="file">./include/label-ja.xml</xsl:variable> 
<xsl:variable name="label" select="document($file)/label"/> 
<!-- その他設定ファイル --> 
<xsl:variable name="standardname" select="document('./include/StandardName.xml')/StandardNames"/> 
<xsl:variable name="regclass" select="document('./include/RegulatoryClassification.xml')/RegulatoryClassifications"/> 
<!-- 薬剤形式 --> 
<xsl:variable name="drugType"> 
	<xsl:choose> 
		<xsl:when test="ns:PackIns/@drugType='Vaccine'"> 
			<xsl:value-of select="'Vaccine'"/> 
		</xsl:when> 
		<xsl:when test="ns:PackIns/@drugType='Antitoxin'"> 
			<xsl:value-of select="'Antitoxin'"/> 
		</xsl:when> 
		<xsl:when test="ns:PackIns/@drugType='BloodProduct'"> 
			<xsl:value-of select="'BloodProduct'"/> 
		</xsl:when> 
		<xsl:otherwise> 
			<xsl:value-of select="'Medicine'"/> 
		</xsl:otherwise> 
	</xsl:choose> 
</xsl:variable> 
<!-- トップノード用テンプレート --> 
<xsl:template match="ns:PackIns"> 
<html lang="ja"> 
<head> 
	<meta charset="UTF-8"/> 
	<meta http-equiv="x-ua-compatible" content="IE=11" /> 
	<title>添付文書XMLプレビュー</title> 
	<link rel="stylesheet" type="text/css" href="./css/preview.css" /> 
	<script type="text/javascript" src="./js/jquery-3.2.1.min.js"></script> 
	<script type="text/javascript" src="./js/preview.js"></script> 
</head> 
<body> 
<div class="container"> 
	<h1 class="header"> 
		<xsl:apply-templates select="." mode="Join-PROC"> 
			<xsl:with-param name="element" select="/ns:PackIns/ns:ApprovalEtc/ns:DetailBrandName/ns:ApprovalBrandName" /> 
			<xsl:with-param name="separator" select="'／'" /> 
			<xsl:with-param name="content" select="'content-TYPE'" /> 
		</xsl:apply-templates> 
	</h1> 
	<div class="contents"> 
		<!-- 添付文書番号 --> 
		<xsl:apply-templates select="ns:PackageInsertNo" mode="Section-BLK"> 
			<xsl:with-param name="mode" select="'contentBaseWithXMLLANGoptional-TYPE'" /> 
			<xsl:with-param name="id" select="'HDR_PackageInsertNo'" /> 
		</xsl:apply-templates> 
		<!-- 企業コード --> 
		<xsl:apply-templates select="ns:CompanyIdentifier" mode="Section-BLK"> 
			<xsl:with-param name="mode" select="'contentBaseWithXMLLANGoptional-TYPE'" /> 
			<xsl:with-param name="id" select="'HDR_CompanyIdentifier'" /> 
		</xsl:apply-templates> 
		<!-- 作成又は改訂年月 --> 
		<xsl:apply-templates select="ns:DateOfPreparationOrRevision" mode="Section-BLK"> 
			<xsl:with-param name="id" select="'HDR_DateOfPreparationOrRevision'" /> 
		</xsl:apply-templates> 
		<!-- 日本標準商品分類番号 --> 
		<xsl:apply-templates select="ns:Sccj" mode="Section-BLK"> 
			<xsl:with-param name="mode" select="'RepeatedContentBaseWithXMLLANGoptional-O-TYPE'" /> 
			<xsl:with-param name="element" select="ns:Sccj/ns:SccjNo" /> 
			<xsl:with-param name="id" select="'HDR_Sccj'" /> 
			<xsl:with-param name="modifiedflg" select="'true'" /> 
		</xsl:apply-templates> 
		<!-- 薬効分類名 --> 
		<xsl:apply-templates select="ns:TherapeuticClassification" mode="Section-BLK"> 
			<xsl:with-param name="mode" select="'RepeatedDetails-TYPE'" /> 
			<xsl:with-param name="element" select="ns:TherapeuticClassification/ns:Detail" /> 
			<xsl:with-param name="id" select="'HDR_TherapeuticClassification'" /> 
			<xsl:with-param name="modifiedflg" select="'true'" /> 
		</xsl:apply-templates> 
		<!-- 承認等 --> 
		<xsl:apply-templates select="ns:ApprovalEtc" mode="Section-BLK"> 
			<xsl:with-param name="id" select="'HDR_ApprovalEtc'" /> 
		</xsl:apply-templates> 
		<!-- 名称 --> 
		<xsl:apply-templates select="ns:GenericName" mode="Section-BLK"> 
			<xsl:with-param name="mode" select="'RepeatedDetails-TYPE'" /> 
			<xsl:with-param name="element" select="ns:GenericName/ns:Detail" /> 
			<xsl:with-param name="id" select="'HDR_GenericName'" /> 
			<xsl:with-param name="modifiedflg" select="'true'" /> 
		</xsl:apply-templates> 
		<!-- ワクチン株の補足情報 --> 
		<xsl:if test="$drugType='Vaccine'"> 
			<xsl:apply-templates select="ns:SupplementaryInformaitonOfVaccineStrain" mode="Section-BLK"> 
				<xsl:with-param name="title" select="'NONE'" /> 
				<xsl:with-param name="mode" select="'VariousForm-TYPE'" /> 
				<xsl:with-param name="id" select="'HDR_SupplementaryInformaitonOfVaccineStrain'" /> 
				<xsl:with-param name="modifiedflg" select="'true'" /> 
			</xsl:apply-templates> 
		</xsl:if> 
		<!-- 特殊記載項目 --> 
		<xsl:if test="count(ns:SpeciallyDescribedItems)!=0"> 
			<xsl:apply-templates select="ns:SpeciallyDescribedItems" mode="Section-BLK"> 
				<xsl:with-param name="title" select="'NONE'" /> 
				<xsl:with-param name="mode" select="'RepeatedDetails-TYPE'" /> 
				<xsl:with-param name="element" select="ns:SpeciallyDescribedItems/ns:Detail" /> 
				<xsl:with-param name="localname" select="'SpeciallyDescribedItems'" /> 
				<xsl:with-param name="localElement" select="ns:SpeciallyDescribedItems" /> 
				<xsl:with-param name="id" select="'HDR_SpeciallyDescribedItems'" /> 
			</xsl:apply-templates> 
		</xsl:if> 
		<!-- 1. 警告 --> 
		<xsl:if test="count(ns:Warnings)!=0"> 
			<div class="frame red"> 
				<xsl:apply-templates select="ns:Warnings" mode="Section-BLK"> 
					<xsl:with-param name="index" select="1" /> 
					<xsl:with-param name="level" select="1" /> 
					<xsl:with-param name="mode" select="'VariousForm-TYPE'" /> 
				</xsl:apply-templates> 
			</div> 
		</xsl:if> 
		<!-- 2. 禁忌 --> 
		<xsl:if test="count(ns:ContraIndications)!=0"> 
			<div class="frame frame-red"> 
				<xsl:apply-templates select="ns:ContraIndications" mode="Section-BLK"> 
					<xsl:with-param name="title"> 
						<xsl:value-of select="$label/ContraIndications/Item[@id=$drugType]" /> 
					</xsl:with-param> 
					<xsl:with-param name="index" select="2" /> 
					<xsl:with-param name="level" select="1" /> 
					<xsl:with-param name="mode" select="'VariousForm-TYPE'" /> 
				</xsl:apply-templates> 
			</div> 
		</xsl:if> 
		<!-- 3. 組成・性状 --> 
		<xsl:if test="count(ns:CompositionAndProperty/ns:OverviewOfRecipe)!=0 or count(ns:CompositionAndProperty/ns:Composition)!=0 or count(ns:CompositionAndProperty/ns:Property)!=0"> 
			<xsl:apply-templates select="ns:CompositionAndProperty" mode="Section-BLK"> 
				<xsl:with-param name="title"> 
					<xsl:value-of select="$label/CompositionAndProperty/Item[@id=$drugType]" /> 
				</xsl:with-param> 
				<xsl:with-param name="index" select="3" /> 
				<xsl:with-param name="level" select="1" /> 
			</xsl:apply-templates> 
		</xsl:if> 
		<!-- 4. 効能又は効果 --> 
		<xsl:apply-templates select="ns:IndicationsOrEfficacy" mode="Section-BLK"> 
			<xsl:with-param name="title"> 
				<xsl:variable name="id" select="ns:IndicationsOrEfficacy/@wordingPatternOfIndications" /> 
				<xsl:value-of select="$label/IndicationsOrEfficacy/Item[@id=$id]" /> 
			</xsl:with-param> 
			<xsl:with-param name="index" select="4" /> 
			<xsl:with-param name="level" select="1" /> 
			<xsl:with-param name="mode" select="'VariousForm-TYPE'" /> 
		</xsl:apply-templates> 
		<!-- 5. 効能又は効果に関連する注意 --> 
		<xsl:apply-templates select="ns:EfficacyRelatedPrecautions" mode="Section-BLK"> 
			<xsl:with-param name="title"> 
				<xsl:variable name="id" select="ns:EfficacyRelatedPrecautions/@wordingPatternOfEfficacyRelatedPrecautions" /> 
				<xsl:value-of select="$label/EfficacyRelatedPrecautions/Item[@id=$id]" /> 
			</xsl:with-param> 
			<xsl:with-param name="index" select="5" /> 
			<xsl:with-param name="level" select="1" /> 
			<xsl:with-param name="mode" select="'VariousForm-TYPE'" /> 
		</xsl:apply-templates> 
		<!-- 6. 用法及び用量 --> 
		<xsl:apply-templates select="ns:InfoDoseAdmin[count(./*[not(contains(local-name(),'Obsolete-SGML-'))])>0]" mode="Section-BLK"> 
			<xsl:with-param name="title"> 
				<xsl:variable name="id" select="ns:InfoDoseAdmin/@wordingPatternOfDoseAdmin" /> 
				<xsl:value-of select="$label/InfoDoseAdmin/Item[@id=$id]" /> 
			</xsl:with-param> 
			<xsl:with-param name="index" select="6" /> 
			<xsl:with-param name="level" select="1" /> 
		</xsl:apply-templates> 
		<!-- 7. 用法及び用量に関連する注意 --> 
		<xsl:apply-templates select="ns:InfoPrecautionsDosage" mode="Section-BLK"> 
			<xsl:with-param name="title"> 
				<xsl:variable name="id" select="ns:InfoPrecautionsDosage/@wordingPatternOfInfoPrecautionsDosage" /> 
				<xsl:value-of select="$label/InfoPrecautionsDosage/Item[@id=$id]" /> 
			</xsl:with-param> 
			<xsl:with-param name="index" select="7" /> 
			<xsl:with-param name="level" select="1" /> 
			<xsl:with-param name="mode" select="'VariousForm-TYPE'" /> 
		</xsl:apply-templates> 
		<!-- 8. 重要な基本的注意 --> 
		<xsl:apply-templates select="ns:ImportantPrecautions" mode="Section-BLK"> 
			<xsl:with-param name="index" select="8" /> 
			<xsl:with-param name="level" select="1" /> 
			<xsl:with-param name="mode" select="'VariousForm-TYPE'" /> 
		</xsl:apply-templates> 
		<!-- 9. 特定の背景を有する患者に関する注意 --> 
		<xsl:apply-templates select="ns:UseInSpecificPopulations[count(./*[not(contains(local-name(),'Obsolete-SGML-'))])>0]" mode="Section-BLK"> 
			<xsl:with-param name="title"> 
				<xsl:value-of select="$label/UseInSpecificPopulations/Item[@id=$drugType]" /> 
			</xsl:with-param> 
			<xsl:with-param name="index" select="9" /> 
			<xsl:with-param name="level" select="1" /> 
		</xsl:apply-templates> 
		<!-- 10. 相互作用 --> 
		<xsl:apply-templates select="ns:Interactions[count(./*[not(contains(local-name(),'Obsolete-SGML-'))])>0]" mode="Section-BLK"> 
			<xsl:with-param name="index" select="10" /> 
			<xsl:with-param name="level" select="1" /> 
		</xsl:apply-templates> 
		<!-- 11. 副作用 --> 
		<xsl:apply-templates select="ns:AdverseEvents[count(./*[not(contains(local-name(),'Obsolete-SGML-'))])>0]" mode="Section-BLK"> 
			<xsl:with-param name="title"> 
				<xsl:value-of select="$label/AdverseEvents/Item[@id=$drugType]" /> 
			</xsl:with-param> 
			<xsl:with-param name="index" select="11" /> 
			<xsl:with-param name="level" select="1" /> 
		</xsl:apply-templates> 
		<!-- 12. 臨床検査結果に及ぼす影響 --> 
		<xsl:apply-templates select="ns:InfluenceOnLaboratoryValues" mode="Section-BLK"> 
			<xsl:with-param name="index" select="12" /> 
			<xsl:with-param name="level" select="1" /> 
			<xsl:with-param name="mode" select="'VariousForm-TYPE'" /> 
		</xsl:apply-templates> 
		<!-- 13. 過量投与 --> 
		<xsl:apply-templates select="ns:OverDosage" mode="Section-BLK"> 
			<xsl:with-param name="title"> 
				<xsl:value-of select="$label/OverDosage/Item[@id=$drugType]" /> 
			</xsl:with-param> 
			<xsl:with-param name="index" select="13" /> 
			<xsl:with-param name="level" select="1" /> 
			<xsl:with-param name="mode" select="'VariousForm-TYPE'" /> 
		</xsl:apply-templates> 
		<!-- 14. 適用上の注意 --> 
		<xsl:apply-templates select="ns:PrecautionsForApplication" mode="Section-BLK"> 
			<xsl:with-param name="index" select="14" /> 
			<xsl:with-param name="level" select="1" /> 
		</xsl:apply-templates> 
		<!-- 15. その他の注意 --> 
		<xsl:apply-templates select="ns:OtherPrecautions" mode="Section-BLK"> 
			<xsl:with-param name="index" select="15" /> 
			<xsl:with-param name="level" select="1" /> 
		</xsl:apply-templates> 
		<!-- 16. 薬物動態 --> 
		<xsl:apply-templates select="ns:Pharmacokinetics" mode="Section-BLK"> 
			<xsl:with-param name="index" select="16" /> 
			<xsl:with-param name="level" select="1" /> 
		</xsl:apply-templates> 
		<!-- 17. 臨床成績 --> 
		<xsl:apply-templates select="ns:ResultsOfClinicalTrials" mode="Section-BLK"> 
			<xsl:with-param name="index" select="17" /> 
			<xsl:with-param name="level" select="1" /> 
		</xsl:apply-templates> 
		<!-- 18. 薬効薬理 --> 
		<xsl:apply-templates select="ns:EfficacyPharmacology" mode="Section-BLK"> 
			<xsl:with-param name="index" select="18" /> 
			<xsl:with-param name="level" select="1" /> 
		</xsl:apply-templates> 
		<!-- 19. 有効成分に関する理化学的知見 --> 
		<xsl:apply-templates select="ns:PhyschemOfActIngredients[count(./*[not(contains(local-name(),'Obsolete-SGML-'))])>0]" mode="Section-BLK"> 
			<xsl:with-param name="index" select="19" /> 
			<xsl:with-param name="level" select="1" /> 
		</xsl:apply-templates> 
		<!-- 20. 取扱い上の注意 --> 
		<xsl:apply-templates select="ns:PrecautionsForHandling" mode="Section-BLK"> 
			<xsl:with-param name="index" select="20" /> 
			<xsl:with-param name="level" select="1" /> 
			<xsl:with-param name="mode" select="'VariousForm-TYPE'" /> 
		</xsl:apply-templates> 
		<!-- 21. 承認条件 --> 
		<xsl:apply-templates select="ns:ConditionsOfApproval" mode="Section-BLK"> 
			<xsl:with-param name="index" select="21" /> 
			<xsl:with-param name="level" select="1" /> 
			<xsl:with-param name="mode" select="'VariousForm-TYPE'" /> 
		</xsl:apply-templates> 
		<!-- 22. 包装 --> 
		<xsl:apply-templates select="ns:Package" mode="Section-BLK"> 
			<xsl:with-param name="index" select="22" /> 
			<xsl:with-param name="level" select="1" /> 
			<xsl:with-param name="mode" select="'VariousForm-TYPE'" /> 
		</xsl:apply-templates> 
		<!-- 23. 主要文献 --> 
		<xsl:apply-templates select="ns:MainLiterature" mode="Section-BLK"> 
			<xsl:with-param name="index" select="23" /> 
			<xsl:with-param name="level" select="1" /> 
		</xsl:apply-templates> 
		<!-- 24. 文献請求先及び問い合わせ先 --> 
		<xsl:apply-templates select="ns:AddresseeOfLiteratureRequest[count(./*[not(contains(local-name(),'Obsolete-SGML-'))])>0]" mode="Section-BLK"> 
			<xsl:with-param name="index" select="24" /> 
			<xsl:with-param name="level" select="1" /> 
			<xsl:with-param name="mode" select="'RepeatedElement-BLK'" /> 
			<xsl:with-param name="element" select="ns:AddresseeOfLiteratureRequest/ns:AddresseeInfo" /> 
		</xsl:apply-templates> 
		<!-- 25. 保険給付上の注意 --> 
		<xsl:apply-templates select="ns:AttentionOfInsurance" mode="Section-BLK"> 
			<xsl:with-param name="index" select="25" /> 
			<xsl:with-param name="level" select="1" /> 
		</xsl:apply-templates> 
		<!-- 26. 製造販売業者等 --> 
		<xsl:apply-templates select="ns:NameAddressManufact[count(./*[not(contains(local-name(),'Obsolete-SGML-'))])>0]" mode="Section-BLK"> 
			<xsl:with-param name="index" select="26" /> 
			<xsl:with-param name="level" select="1" /> 
			<xsl:with-param name="mode" select="'RepeatedElement-BLK'" /> 
			<xsl:with-param name="element" select="ns:NameAddressManufact/ns:Manufacturer" /> 
		</xsl:apply-templates> 
		<!-- 参考情報 --> 
    <xsl:if test="count(ns:ReferenceInformation)!=0"> 
      <br/> 
      <br/> 
    </xsl:if> 
    <xsl:apply-templates select="ns:ReferenceInformation" mode="Section-BLK"> 
      <xsl:with-param name="title" select="'NONE'" /> 
      <xsl:with-param name="localname" select="'ReferenceInformation'" /> 
      <xsl:with-param name="localElement" select="ns:ReferenceInformation" /> 
      <xsl:with-param name="mode" select="'VariousForm-TYPE'" /> 
      <xsl:with-param name="id" select="'HDR_ReferenceInformation'" /> 
      <xsl:with-param name="modifiedflg" select="'true'" /> 
    </xsl:apply-templates> 
	</div> 
</div> 
<!-- 見出し参照用 --> 
<div id="Header-data" style="display:none;"> 
	<xsl:apply-templates select="ns:Warnings" mode="VariousForm-ForHeaderRef"> 
		<xsl:with-param name="index" select="1" /> 
		<xsl:with-param name="level" select="1" /> 
	</xsl:apply-templates> 
	<xsl:apply-templates select="ns:ContraIndications" mode="VariousForm-ForHeaderRef"> 
		<xsl:with-param name="index" select="2" /> 
		<xsl:with-param name="level" select="1" /> 
	</xsl:apply-templates> 
	<xsl:apply-templates select="ns:CompositionAndProperty" mode="ForHeaderRef"> 
		<xsl:with-param name="index" select="3" /> 
		<xsl:with-param name="level" select="1" /> 
	</xsl:apply-templates> 
	<xsl:apply-templates select="ns:IndicationsOrEfficacy" mode="VariousForm-ForHeaderRef"> 
		<xsl:with-param name="index" select="4" /> 
		<xsl:with-param name="level" select="1" /> 
	</xsl:apply-templates> 
	<xsl:apply-templates select="ns:EfficacyRelatedPrecautions" mode="VariousForm-ForHeaderRef"> 
		<xsl:with-param name="index" select="5" /> 
		<xsl:with-param name="level" select="1" /> 
	</xsl:apply-templates> 
	<xsl:apply-templates select="ns:InfoDoseAdmin" mode="ForHeaderRef" /> 
	<xsl:apply-templates select="ns:InfoPrecautionsDosage" mode="VariousForm-ForHeaderRef"> 
		<xsl:with-param name="index" select="7" /> 
		<xsl:with-param name="level" select="1" /> 
	</xsl:apply-templates> 
	<xsl:apply-templates select="ns:ImportantPrecautions" mode="VariousForm-ForHeaderRef"> 
		<xsl:with-param name="index" select="8" /> 
		<xsl:with-param name="level" select="1" /> 
	</xsl:apply-templates> 
	<xsl:apply-templates select="ns:UseInSpecificPopulations" mode="ForHeaderRef" /> 
	<xsl:apply-templates select="ns:Interactions" mode="ForHeaderRef" /> 
	<xsl:apply-templates select="ns:AdverseEvents" mode="ForHeaderRef" /> 
	<xsl:apply-templates select="ns:InfluenceOnLaboratoryValues" mode="VariousForm-ForHeaderRef"> 
		<xsl:with-param name="index" select="12" /> 
		<xsl:with-param name="level" select="1" /> 
	</xsl:apply-templates> 
	<xsl:apply-templates select="ns:OverDosage" mode="VariousForm-ForHeaderRef"> 
		<xsl:with-param name="index" select="13" /> 
		<xsl:with-param name="level" select="1" /> 
	</xsl:apply-templates> 
	<xsl:apply-templates select="ns:PrecautionsForApplication" mode="ForHeaderRef" /> 
	<xsl:apply-templates select="ns:OtherPrecautions" mode="ForHeaderRef" /> 
	<xsl:apply-templates select="ns:Pharmacokinetics" mode="ForHeaderRef" /> 
	<xsl:apply-templates select="ns:ResultsOfClinicalTrials" mode="ForHeaderRef" /> 
	<xsl:apply-templates select="ns:EfficacyPharmacology" mode="ForHeaderRef" /> 
	<xsl:apply-templates select="ns:PhyschemOfActIngredients" mode="Single-ForHeaderRef"> 
		<xsl:with-param name="index" select="19" /> 
	</xsl:apply-templates> 
	<xsl:apply-templates select="ns:PrecautionsForHandling" mode="VariousForm-ForHeaderRef"> 
		<xsl:with-param name="index" select="20" /> 
		<xsl:with-param name="level" select="1" /> 
	</xsl:apply-templates> 
	<xsl:apply-templates select="ns:ConditionsOfApproval" mode="VariousForm-ForHeaderRef"> 
		<xsl:with-param name="index" select="21" /> 
		<xsl:with-param name="level" select="1" /> 
	</xsl:apply-templates> 
	<xsl:apply-templates select="ns:Package" mode="Single-ForHeaderRef"> 
		<xsl:with-param name="index" select="22" /> 
	</xsl:apply-templates> 
	<xsl:apply-templates select="ns:MainLiterature" mode="Single-ForHeaderRef"> 
		<xsl:with-param name="index" select="23" /> 
	</xsl:apply-templates> 
	<xsl:apply-templates select="ns:AddresseeOfLiteratureRequest" mode="Single-ForHeaderRef"> 
		<xsl:with-param name="index" select="24" /> 
	</xsl:apply-templates> 
	<xsl:apply-templates select="ns:AttentionOfInsurance" mode="ForHeaderRef" /> 
	<xsl:apply-templates select="ns:NameAddressManufact" mode="Single-ForHeaderRef"> 
		<xsl:with-param name="index" select="26" /> 
	</xsl:apply-templates> 
</div> 
</body> 
</html> 
</xsl:template> 
	<xsl:include href="./include/preview-include.xsl" /> 
</xsl:stylesheet> 
