<?xml version="1.0" encoding="UTF-8" ?>

<!-- XSLTスタイルシート宣言-->
<xsl:stylesheet version="1.0"
	xmlns:ns="http://info.pmda.go.jp/namespace/prescription_drugs/package_insert/1.0"
	xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

	<!-- 出力形式 -->
	<xsl:output method="html" doctype-system="about:legacy-compat" encoding="UTF-8" />


	<!-- Section-BLK タイトルと本文部分に分かれた文書構造 -->
	<xsl:template match="ns:*" mode="Section-BLK">
		<xsl:param name="title" select="''" />
		<xsl:param name="titleMode" select="''" />
		<xsl:param name="mode" select="''" />
		<xsl:param name="element" select="ns:*" />
		<xsl:param name="index" select="''" />
		<xsl:param name="level" select="'99'" />
		<xsl:param name="id" select="''" />
		<xsl:param name="modifiedflg" select="''" />
		<!-- H29添付文書XML化対応 START -->
		<xsl:param name="loopCounter" select="''" />
		<!-- H29添付文書XML化対応 END -->
		<xsl:variable name="localname" select="local-name(self::node())" />
		<xsl:choose>
			<xsl:when test="@id!=''">
				<a>
					<xsl:attribute name="name"><xsl:value-of select="@id" /></xsl:attribute>
				</a>
			</xsl:when>
			<xsl:when test="$id!=''">
				<a>
					<xsl:attribute name="name"><xsl:value-of select="$id" /></xsl:attribute>
				</a>
			</xsl:when>
		</xsl:choose>
		<div class="section">
			<!-- 見出しIDの付与 -->
			<xsl:choose>
				<xsl:when test="@id!=''">
					<xsl:attribute name="id"><xsl:value-of select="@id" /></xsl:attribute>
				</xsl:when>
				<xsl:when test="$id!=''">
					<xsl:attribute name="id"><xsl:value-of select="$id" /></xsl:attribute>
				</xsl:when>
			</xsl:choose>
			<!-- modified属性の処理 -->
			<xsl:if test="$index!=''">
				<!-- セクションレベル属性 -->
				<xsl:attribute name="data-level">
					<xsl:value-of select="$level" />
				</xsl:attribute>
				<xsl:apply-templates select="self::node()" mode="addModified" >
					<xsl:with-param name="mode" select="$mode" />
				</xsl:apply-templates>
			</xsl:if>

			<!-- 項番なしの項目でも改訂記号を表示する場合 -->
			<xsl:if test="$index='' and $modifiedflg!=''">
				<xsl:attribute name="data-level">
					<xsl:value-of select="$level" />
				</xsl:attribute>
				<xsl:apply-templates select="self::node()" mode="addModified" >
					<xsl:with-param name="mode" select="$mode" />
					<xsl:with-param name="localname" select="$localname" />
				</xsl:apply-templates>
			</xsl:if>

			<h3 class="section_header">
				<!-- 項番付与 -->
				<xsl:if test="$index!=''">
					<xsl:choose>
						<xsl:when test="contains($index, '.')">
							<xsl:value-of select="concat($index, ' ')" />
						</xsl:when>
						<xsl:otherwise>
							<xsl:value-of select="concat($index, '. ')" />
						</xsl:otherwise>
					</xsl:choose>
				</xsl:if>
				<!-- タイトル -->
				<xsl:choose>
					<xsl:when test="$titleMode='content-TYPE'">
						<xsl:apply-templates select="$title" mode="content-TYPE" />
					</xsl:when>
					<xsl:when test="$title=''">
						<xsl:value-of select="$label/*[local-name()=$localname]" />
					</xsl:when>
					<xsl:when test="$title!='NONE'">
						<xsl:value-of select="$title" />
					</xsl:when>
				</xsl:choose>
			</h3>
			<div>
				<xsl:if test="$localname='SpeciallyDescribedItems'">
					<xsl:attribute name="style"><xsl:value-of select="'margin-left: 0px;'" /></xsl:attribute>
				</xsl:if>
				<xsl:attribute name="class">
					level-<xsl:value-of select="$level" />
				</xsl:attribute>
				<xsl:attribute name="data-index">
					<xsl:value-of select="$index" />
				</xsl:attribute>
				<xsl:choose>
					<xsl:when test="$mode='RepeatedElement-BLK'">
						<xsl:apply-templates select="self::node()" mode="RepeatedElement-BLK">
							<xsl:with-param name="element" select="$element" />
						</xsl:apply-templates>
					</xsl:when>
					<xsl:when test="$mode='RepeatedContentBaseWithXMLLANGoptional-O-TYPE'">
						<xsl:apply-templates select="self::node()" mode="RepeatedContentBaseWithXMLLANGoptional-O-TYPE">
							<xsl:with-param name="element" select="$element" />
						</xsl:apply-templates>
					</xsl:when>
					<xsl:when test="$mode='RepeatedDetails-TYPE'">
						<xsl:apply-templates select="self::node()" mode="RepeatedDetails-TYPE">
							<xsl:with-param name="element" select="$element" />
							<xsl:with-param name="localname" select="$localname" />
						</xsl:apply-templates>
					</xsl:when>
					<xsl:when test="$mode='VariousForm-TYPE'">
						<xsl:apply-templates select="self::node()" mode="VariousForm-TYPE">
							<xsl:with-param name="index" select="$index" />
							<xsl:with-param name="level" select="$level" />
						</xsl:apply-templates>
					</xsl:when>
					<xsl:when test="$mode='HeaderDetailList-TYPE'">
						<ul class="HeaderDetailList">
							<xsl:apply-templates select="self::node()" mode="HeaderDetailList-TYPE" />
						</ul>
					</xsl:when>
					<xsl:when test="$mode='content-TYPE'">
						<xsl:apply-templates select="self::node()" mode="content-TYPE" />
					</xsl:when>
					<xsl:when test="$mode='contentBaseWithXMLLANGoptional-TYPE'">
						<xsl:apply-templates select="self::node()" mode="contentBaseWithXMLLANGoptional-TYPE" >
							<xsl:with-param name="modifiedflg" select="$modifiedflg" />
						</xsl:apply-templates>
					</xsl:when>
					<xsl:when test="$mode='DrugType'">
						<xsl:call-template name="DrugType" />
					</xsl:when>
					<!-- H29添付文書XML化対応 START -->
					<xsl:when test="$loopCounter!=''">
						<xsl:apply-templates select="self::node()">
							<xsl:with-param name="loopCounter" select="$loopCounter" />
						</xsl:apply-templates>
					</xsl:when>
					<!-- H29添付文書XML化対応 END -->
					<xsl:otherwise>
						<xsl:apply-templates select="self::node()" />
					</xsl:otherwise>
				</xsl:choose>
			</div>
		</div>
	</xsl:template>

	<!-- 添付文書形式 -->
	<xsl:template name="DrugType">
		<p>
			<xsl:value-of select="$label/DrugTypeItems/Item[@id=$drugType]" />
		</p>
	</xsl:template>

	<!-- 改訂情報の個数を追加する -->
	<xsl:template match="ns:*" mode="addModified">
		<xsl:param name="localname" select="''" />
		<xsl:param name="mode" select="''" />
		<!-- 配下の改訂記号をカウント -->
		<xsl:choose>
			<!-- DetailBrandNameはApprovalBrandNameをカウント -->
			<xsl:when test="local-name()='DetailBrandName'">
				<xsl:attribute name="data-thisCount">
					<xsl:value-of select="count(self::node()/ns:ApprovalBrandName[contains(@modified,'今回')])" />
				</xsl:attribute>
				<xsl:attribute name="data-lastCount">
					<xsl:value-of select="count(self::node()/ns:ApprovalBrandName[contains(@modified,'前回')])" />
				</xsl:attribute>
			</xsl:when>
			<!-- PhyschemOfActIngredientsSectionはPhyschemOfActIngredientsSectionTitleをカウント -->
			<xsl:when test="local-name()='PhyschemOfActIngredientsSection'">
				<xsl:attribute name="data-thisCount">
					<xsl:value-of select="count(self::node()/ns:PhyschemOfActIngredientsSectionTitle[contains(@modified,'今回')])" />
				</xsl:attribute>
				<xsl:attribute name="data-lastCount">
					<xsl:value-of select="count(self::node()/ns:PhyschemOfActIngredientsSectionTitle[contains(@modified,'前回')])" />
				</xsl:attribute>
			</xsl:when>
			<!-- StandardNameは自身＋子孫 -->
			<xsl:when test="local-name()='StandardName'">
				<xsl:attribute name="data-thisCount">
					<xsl:value-of select="count(self::node()[contains(@modified,'今回')])+count(self::node()//*[contains(@modified,'今回')])" />
				</xsl:attribute>
				<xsl:attribute name="data-lastCount">
					<xsl:value-of select="count(self::node()[contains(@modified,'前回')])+count(self::node()//*[contains(@modified,'前回')])" />
				</xsl:attribute>
			</xsl:when>
			<!-- content-TYPE,contentBaseWithXMLLANGoptional-TYPE,規制区分,特殊記載項目は自身のみ -->
			<xsl:when test="$mode='content-TYPE' or $mode='contentBaseWithXMLLANGoptional-TYPE' or $localname='StartingDateOfMarketing' or local-name()='RegulatoryClassification' or $localname='SpeciallyDescribedItems'">
				<xsl:attribute name="data-thisCount">
					<xsl:value-of select="count(self::node()[contains(@modified,'今回')])" />
				</xsl:attribute>
				<xsl:attribute name="data-lastCount">
					<xsl:value-of select="count(self::node()[contains(@modified,'前回')])" />
				</xsl:attribute>
			</xsl:when>
			<!-- 上記以外(VariousForms-TYPEなど)は子孫 -->
			<xsl:otherwise>
				<xsl:attribute name="data-thisCount">
					<xsl:value-of select="count(self::node()//*[contains(@modified,'今回')])" />
				</xsl:attribute>
				<xsl:attribute name="data-lastCount">
					<xsl:value-of select="count(self::node()//*[contains(@modified,'前回')])" />
				</xsl:attribute>
			</xsl:otherwise>
		</xsl:choose>
	</xsl:template>

	<!-- RepeatedElement-BLK 段落の連続する構造 -->
	<xsl:template match="ns:*" mode="RepeatedElement-BLK">
		<xsl:param name="element" select="ns:*" />
		<xsl:param name="content" select="''" />
		<xsl:param name="localname" select="''" />
		<div>
			<xsl:for-each select="$element">
				<div>
					<xsl:apply-templates select="self::node()" mode="addModified" >
						<xsl:with-param name="localname" select="$localname" />
					</xsl:apply-templates>
					<xsl:if test="$localname='SpeciallyDescribedItems'">
						<xsl:attribute name="data-level">
							<xsl:value-of select="'2'" />
						</xsl:attribute>
						<xsl:attribute name="class"><xsl:value-of select="'frame'" /></xsl:attribute>
						<xsl:attribute name="style"><xsl:value-of select="'margin-left: 0px;'" /></xsl:attribute>
						<span class="section_header"></span>
					</xsl:if>
					<xsl:choose>
						<xsl:when test="$content='content-TYPE'">
							<xsl:apply-templates select="self::node()" mode="content-TYPE" />
						</xsl:when>
						<xsl:when test="$content='contentBaseWithXMLLANGoptional-TYPE'">
							<xsl:apply-templates select="self::node()" mode="contentBaseWithXMLLANGoptional-TYPE" >
								<xsl:with-param name="modifiedflg" select="'true'" />
							</xsl:apply-templates>
						</xsl:when>
						<xsl:otherwise>
							<xsl:apply-templates select="self::node()" >
								<xsl:with-param name="indx" select="position()" />
							</xsl:apply-templates>
						</xsl:otherwise>
					</xsl:choose>
				</div>
			</xsl:for-each>
		</div>
	</xsl:template>

	<xsl:template match="ns:*" mode="OtherInformation-BLK">
		<xsl:param name="index" select="''" />
		<xsl:param name="startIndex" select="1" />
		<xsl:param name="level" select="2" />
		<xsl:for-each select="ns:OtherInformation">
			<xsl:variable name="nowIndex" select="$startIndex+position()-1" />
			<xsl:choose>
				<xsl:when test="$index!=''">
					<xsl:apply-templates select="self::node()" mode="Section-BLK">
						<xsl:with-param name="title" select="ns:Header" />
						<xsl:with-param name="titleMode" select="'content-TYPE'" />
						<xsl:with-param name="mode" select="'VariousForm-TYPE'" />
						<xsl:with-param name="index" select="concat($index,'.',$nowIndex)" />
						<xsl:with-param name="level" select="'2'" />
						<xsl:with-param name="modifiedflg" select="'true'" />
					</xsl:apply-templates>
				</xsl:when>
				<xsl:otherwise>
					<xsl:apply-templates select="self::node()" mode="Section-BLK">
						<xsl:with-param name="title" select="ns:Header" />
						<xsl:with-param name="titleMode" select="'content-TYPE'" />
						<xsl:with-param name="mode" select="'VariousForm-TYPE'" />
						<xsl:with-param name="level" select="$level" />
						<xsl:with-param name="modifiedflg" select="'true'" />
					</xsl:apply-templates>
				</xsl:otherwise>
			</xsl:choose>
		</xsl:for-each>
	</xsl:template>


	<!-- Join-PROCデータ文字列のjoin処理 -->
	<xsl:template match="ns:*" mode="Join-PROC">
		<xsl:param name="element" select="ns:*" />
		<xsl:param name="content" select="''" />
		<xsl:param name="separator" select="'、'" />
		<xsl:for-each select="$element">
			<xsl:if test="position() != 1">
				<xsl:value-of select="$separator" />
			</xsl:if>
			<xsl:choose>
				<xsl:when test="$content='content-TYPE'">
					<xsl:apply-templates select="." mode="content-TYPE" />
				</xsl:when>
				<xsl:when test="$content='contentBaseWithXMLLANGoptional-TYPE'">
					<xsl:apply-templates select="." mode="contentBaseWithXMLLANGoptional-TYPE" />
				</xsl:when>
				<xsl:otherwise>
					<xsl:apply-templates select="." />
				</xsl:otherwise>
			</xsl:choose>
		</xsl:for-each>
	</xsl:template>


	<!-- 作成又は改訂年月 -->
	<xsl:template match="ns:DateOfPreparationOrRevision">
		<table>
			<xsl:for-each select="ns:PreparationOrRevision">
				<!-- 表示は「今回」「前回」の順 -->
				<xsl:sort select="./@id" data-type="text" order="ascending" />
				<xsl:variable name="createCount" select="count(@created)" />
				<xsl:variable name="mark">
					<xsl:variable name="data-thisCount" select="count(//*[contains(@modified,'今回')])" />
					<xsl:variable name="data-lastCount" select="count(//*[contains(@modified,'前回')])" />
					<xsl:choose>
						<!-- 改訂情報が今回のみの場合 -->
						<xsl:when test="count(//ns:PreparationOrRevision[contains(@id,'前回')])=0">
							<!-- modified属性が設定されていない -->
							<xsl:choose>
								<!-- XML内にmodified属性が1つも設定されていない場合、改訂記号を付けない -->
								<xsl:when test="$data-thisCount=0 and $data-lastCount=0">
									<xsl:choose>
										<xsl:when test="@id='今回'"></xsl:when>
									</xsl:choose>
								</xsl:when>
								<!-- XML内にmodified属性が設定されている場合、改訂記号を付ける -->
								<xsl:otherwise>
									<xsl:choose>
										<xsl:when test="@id='今回'">＊</xsl:when>
									</xsl:choose>
								</xsl:otherwise>
							</xsl:choose>
						</xsl:when>
						<!-- 改訂情報に今回と前回を設定している場合 -->
						<xsl:otherwise>
							<xsl:choose>
								<!-- XML内にmodified属性が1つも設定されていなかったら、前回の改訂記号は付けず、今回の改訂記号は「*」とする -->
								<xsl:when test="$data-thisCount=0 and $data-lastCount=0">
									<xsl:choose>
										<xsl:when test="@id='今回'">＊</xsl:when>
										<xsl:when test="@id='前回'"></xsl:when>
									</xsl:choose>
								</xsl:when>
								<!-- XML内にmodified属性が今回のみの場合、前回の改訂記号は付けず、今回の改訂記号は「*」とする -->
								<xsl:when test="$data-thisCount!=0 and $data-lastCount=0">
									<xsl:choose>
										<xsl:when test="@id='今回'">＊</xsl:when>
										<xsl:when test="@id='前回'"></xsl:when>
									</xsl:choose>
								</xsl:when>
								<!-- XML内のmodified属性が設定されている場合、前回の改訂記号は「*」とし、今回の改訂記号は「**」とする -->
								<xsl:otherwise>
									<xsl:choose>
										<xsl:when test="@id='今回'">＊＊</xsl:when>
										<xsl:when test="@id='前回'">＊</xsl:when>
									</xsl:choose>
								</xsl:otherwise>
							</xsl:choose>
						</xsl:otherwise>
					</xsl:choose>
				</xsl:variable>
				<xsl:variable name="yearMonth" select="ns:YearMonth" />
				<xsl:variable name="version" select="ns:Version/ns:Lang[@xml:lang=$lang]" />
				<xsl:variable name="reasonForRevision" select="ns:ReasonForRevision/ns:Lang[@xml:lang=$lang]" />
				<tr>
					<td><xsl:value-of select="$mark" /></td>
					<xsl:if test="$lang='ja'">
						<td><xsl:value-of select="substring($yearMonth, 1, 4)" />年
						<xsl:choose>
							<xsl:when test="$createCount=0">
								<xsl:choose>
									<xsl:when test="substring($yearMonth, 6, 1)=0"><xsl:value-of select="substring($yearMonth, 7, 1)" />月改訂</xsl:when>
									<xsl:otherwise><xsl:value-of select="substring($yearMonth, 6, 2)" />月改訂</xsl:otherwise>
								</xsl:choose>
							</xsl:when>
							<xsl:when test="$createCount!=0">
								<xsl:choose>
									<xsl:when test="substring($yearMonth, 6, 1)=0"><xsl:value-of select="substring($yearMonth, 7, 1)" />月作成</xsl:when>
									<xsl:otherwise><xsl:value-of select="substring($yearMonth, 6, 2)" />月作成</xsl:otherwise>
								</xsl:choose>
							</xsl:when>
						</xsl:choose>
						<xsl:if test="$version!='' or $reasonForRevision!=''">
							(
						</xsl:if>
						<xsl:if test="$version!=''">
							<xsl:apply-templates select="ns:Version" mode="content-TYPE" />
						</xsl:if>
						<xsl:if test="$reasonForRevision!=''">
							<xsl:if test="$version!=''">
								、
							</xsl:if>
							<xsl:apply-templates select="ns:ReasonForRevision" mode="content-TYPE" />
						</xsl:if>
						<xsl:if test="$version!='' or $reasonForRevision!=''">
							)
						</xsl:if>
						</td>
					</xsl:if>
					<xsl:if test="$lang='en'">
						<td><xsl:value-of select="substring($yearMonth, 1, 4)" />/
						<xsl:value-of select="substring($yearMonth, 6, 2)" />
						<xsl:if test="$version!='' or $reasonForRevision!=''">
							(
						</xsl:if>
						<xsl:if test="$version!=''">
							<xsl:apply-templates select="ns:Version" mode="content-TYPE" />
						</xsl:if>
						<xsl:if test="$reasonForRevision!=''">
							<xsl:if test="$version!=''">
								,
							</xsl:if>
							<xsl:apply-templates select="ns:ReasonForRevision" mode="content-TYPE" />
						</xsl:if>
						<xsl:if test="$version!='' or $reasonForRevision!=''">
							)
						</xsl:if>
						</td>
					</xsl:if>
				</tr>
			</xsl:for-each>
		</table>
	</xsl:template>


	<!-- 承認等 -->
	<xsl:template match="ns:ApprovalEtc">
		<xsl:for-each select="ns:DetailBrandName">
			<!-- H29添付文書XML化対応 START -->
			<a>
				<xsl:attribute name="name">HDR_DetailBrandName_<xsl:value-of select="position()" /></xsl:attribute>
			</a>
			<!-- H29添付文書XML化対応 END -->
			<xsl:apply-templates select="self::node()" mode="Section-BLK">
				<xsl:with-param name="title" select="ns:ApprovalBrandName" />
				<xsl:with-param name="titleMode" select="'content-TYPE'" />
				<xsl:with-param name="modifiedflg" select="'true'" />
				<!-- H29添付文書XML化対応 -->
				<xsl:with-param name="loopCounter" select="position()" />
				<!-- H29添付文書XML化対応 -->
			</xsl:apply-templates>
		</xsl:for-each>
	</xsl:template>

	<!-- 販売名 -->
	<xsl:template match="ns:DetailBrandName">
		<!-- H29添付文書XML化対応 START -->
		<xsl:param name="loopCounter" select="''" />
		<!-- H29添付文書XML化対応 END -->

		<!-- 製品の補足情報 -->
		<xsl:apply-templates select="ns:SupplementaryInformationOfProduct" mode="Section-BLK">
			<xsl:with-param name="title" select="'NONE'" />
			<xsl:with-param name="id" select="concat('HDR_SupplementaryInformationOfProduct_', $loopCounter)" />
		</xsl:apply-templates>
		<!-- 販売名コード -->
		<!-- H29添付文書XML化対応 START -->
		<!-- <xsl:apply-templates select="ns:BrandCode" mode="Section-BLK" /> -->
		<xsl:apply-templates select="ns:BrandCode" mode="Section-BLK">
			<xsl:with-param name="modifiedflg" select="'true'" />
			<xsl:with-param name="id" select="concat('HDR_BrandCode_', $loopCounter)" />
		</xsl:apply-templates>
		<!-- H29添付文書XML化対応 END -->
		<!-- 販売名英字表記 -->
		<xsl:apply-templates select="ns:TrademarkInEnglish" mode="Section-BLK">
			<xsl:with-param name="mode" select="'RepeatedContentBaseWithXMLLANGoptional-O-TYPE'" />
			<xsl:with-param name="element" select="ns:TrademarkInEnglish/ns:TrademarkName" />
			<xsl:with-param name="modifiedflg" select="'true'" />
			<!-- H29添付文書XML化対応 START -->
			<xsl:with-param name="id" select="concat('HDR_TrademarkInEnglish_', $loopCounter)" />
			<!-- H29添付文書XML化対応 END -->
		</xsl:apply-templates>
		<!-- 販売名ひらがな -->
		<xsl:apply-templates select="ns:BrandNameInHiragana" mode="Section-BLK">
			<xsl:with-param name="mode" select="'RepeatedContentBaseWithXMLLANGoptional-O-TYPE'" />
			<xsl:with-param name="element" select="ns:BrandNameInHiragana/ns:NameInHiragana" />
			<xsl:with-param name="modifiedflg" select="'true'" />
			<!-- H29添付文書XML化対応 START -->
			<xsl:with-param name="id" select="concat('HDR_BrandNameInHiragana_', $loopCounter)" />
			<!-- H29添付文書XML化対応 END -->
		</xsl:apply-templates>
		<!-- 承認番号 -->
		<!-- H29添付文書XML化対応 START -->
		<!--<xsl:apply-templates select="ns:ApprovalAndLicenseNo" mode="Section-BLK" />-->
		<xsl:apply-templates select="ns:ApprovalAndLicenseNo" mode="Section-BLK">
			<xsl:with-param name="modifiedflg" select="'true'" />
			<xsl:with-param name="id" select="concat('HDR_ApprovalAndLicenseNo_', $loopCounter)" />
		</xsl:apply-templates>
		<!-- H29添付文書XML化対応 END -->
		<!-- 販売開始年月 -->
		<!-- H29添付文書XML化対応 START -->
		<!--<xsl:apply-templates select="ns:StartingDateOfMarketing" mode="Section-BLK" />-->
		<xsl:apply-templates select="ns:StartingDateOfMarketing" mode="Section-BLK">
			<xsl:with-param name="modifiedflg" select="'true'" />
			<xsl:with-param name="id" select="concat('HDR_StartingDateOfMarketing_', $loopCounter)" />
		</xsl:apply-templates>
		<!-- H29添付文書XML化対応 END -->
		<!-- 貯法、有効期間 -->
		<!-- H29添付文書XML化対応 START -->
		<!--<xsl:apply-templates select="ns:Storage" mode="Section-BLK" />-->
		<xsl:apply-templates select="ns:Storage" mode="Section-BLK">
			<xsl:with-param name="level" select="1" />
			<xsl:with-param name="modifiedflg" select="'true'" />
			<xsl:with-param name="id" select="concat('HDR_Storage_', $loopCounter)" />
		</xsl:apply-templates>
		<!-- H29添付文書XML化対応 END -->
		<!-- 基準名 -->
		<!-- H29添付文書XML化対応 START -->
		<!--<xsl:apply-templates select="ns:StandardName" mode="Section-BLK" />-->
		<xsl:apply-templates select="ns:StandardName" mode="Section-BLK">
			<xsl:with-param name="level" select="'1'" />
			<xsl:with-param name="modifiedflg" select="'true'" />
			<xsl:with-param name="id" select="concat('HDR_StandardName_', $loopCounter)" />
		</xsl:apply-templates>
		<!-- H29添付文書XML化対応 END -->
		<!-- 規制区分 -->
		<!-- H29添付文書XML化対応 START -->
		<xsl:apply-templates select="ns:RegulatoryClassification" mode="Section-BLK" >
			<xsl:with-param name="modifiedflg" select="'true'" />
			<xsl:with-param name="id" select="concat('HDR_RegulatoryClassification_', $loopCounter)" />
		</xsl:apply-templates>
		<!-- H29添付文書XML化対応 END -->
	</xsl:template>

	<!-- 製品の補足情報 -->
	<xsl:template match="ns:SupplementaryInformationOfProduct">
		<xsl:apply-templates select="self::node()" mode="VariousForm-TYPE"/>
	</xsl:template>

	<!-- 販売名コード -->
	<xsl:template match="ns:BrandCode">
		<xsl:apply-templates select="ns:YJCode" mode="Section-BLK">
			<xsl:with-param name="mode" select="'contentBaseWithXMLLANGoptional-TYPE'" />
		</xsl:apply-templates>
	<!-- 2017/12/26 機構様指摘により一般コードは編集対象外とする。
		<xsl:apply-templates select="self::node()" mode="Section-BLK">
			<xsl:with-param name="title" select="$label/Code" />
			<xsl:with-param name="mode" select="'RepeatedElement-BLK'" />
			<xsl:with-param name="element" select="ns:Code" />
		</xsl:apply-templates>
	-->
	</xsl:template>

	<!-- 一般コード -->
	<xsl:template match="ns:Code">
		<xsl:apply-templates select="ns:CodeName" mode="contentBaseWithXMLLANGoptional-TYPE" />
		<xsl:apply-templates select="ns:CodeValue" />
	</xsl:template>

	<!-- 承認番号 -->
	<xsl:template match="ns:ApprovalAndLicenseNo">
		<xsl:apply-templates select="ns:ApprovalNo" mode="Section-BLK">
			<xsl:with-param name="mode" select="'contentBaseWithXMLLANGoptional-TYPE'" />
		</xsl:apply-templates>
		<xsl:apply-templates select="ns:LicenseNo" mode="Section-BLK">
			<xsl:with-param name="mode" select="'contentBaseWithXMLLANGoptional-TYPE'" />
		</xsl:apply-templates>
	</xsl:template>

	<!-- 販売開始年月 -->
	<xsl:template match="ns:StartingDateOfMarketing">
		<xsl:choose>
			<xsl:when test="$lang='ja'">
				<xsl:value-of select="substring(self::node(), 1, 4)" />年
				<xsl:choose>
					<xsl:when test="substring(self::node(), 6, 1)=0">
						<xsl:value-of select="substring(self::node(), 7, 1)" />月
					</xsl:when>
					<xsl:otherwise>
						<xsl:value-of select="substring(self::node(), 6, 2)" />月
					</xsl:otherwise>
				</xsl:choose>
			</xsl:when>
			<xsl:otherwise>
				<xsl:value-of select="substring(self::node(), 1, 4)" />/
				<xsl:choose>
					<xsl:when test="substring(self::node(), 6, 1)=0">
						<xsl:value-of select="substring(self::node(), 7, 1)" />
					</xsl:when>
					<xsl:otherwise>
						<xsl:value-of select="substring(self::node(), 6, 2)" />
					</xsl:otherwise>
				</xsl:choose>
			</xsl:otherwise>
		</xsl:choose>
	</xsl:template>

	<!-- 貯法、有効期間 -->
	<xsl:template match="ns:Storage">
		<xsl:apply-templates select="ns:StorageMethod" mode="Section-BLK">
			<xsl:with-param name="mode" select="'content-TYPE'" />
			<xsl:with-param name="level" select="2" />
			<xsl:with-param name="modifiedflg" select="'true'" />
		</xsl:apply-templates>
		<xsl:apply-templates select="ns:ShelfLife" mode="Section-BLK">
			<xsl:with-param name="mode" select="'content-TYPE'" />
			<xsl:with-param name="level" select="2" />
			<xsl:with-param name="modifiedflg" select="'true'" />
		</xsl:apply-templates>
		<xsl:apply-templates select="self::node()" mode="OtherInformation-BLK"/>
	</xsl:template>

	<!-- 基準名 -->
	<xsl:template match="ns:StandardName">
		<xsl:for-each select="ns:StandardNameCategory">
			<xsl:variable name="codeNum" select="ns:StandardNameCategoryCode" />
			<p>
				<xsl:value-of select="$standardname/Selection/Item[@id=$codeNum]/Label/Lang[@xml:lang=$lang]" />
			</p>
			<xsl:if test="count(ns:StandardNameDetail/ns:Lang[@xml:lang=$lang])!=0">
				<p style="margin-left: 18px;">
					<xsl:apply-templates select="ns:StandardNameDetail" mode="content-TYPE" />
				</p>
			</xsl:if>
		</xsl:for-each>
		<xsl:if test="count(ns:OtherStandardName/ns:OtherStandardNameCategory/ns:Lang[@xml:lang=$lang])!=0">
			<p>
				<xsl:value-of select="ns:OtherStandardName/ns:OtherStandardNameCategory/ns:Lang[@xml:lang=$lang]" />
			</p>
		</xsl:if>
		<xsl:if test="count(ns:OtherStandardName/ns:StandardNameDetail/ns:Lang[@xml:lang=$lang])!=0">
			<p style="margin-left: 18px;">
				<xsl:apply-templates select="ns:OtherStandardName/ns:StandardNameDetail" mode="content-TYPE" />
			</p>
		</xsl:if>
	</xsl:template>

	<!-- 規制区分 -->
	<xsl:template match="ns:RegulatoryClassification">
		<xsl:for-each select="ns:RegulatoryClassificationCodeAndNote">
			<xsl:variable name="codeNum" select="ns:RegulatoryClassificationCode" />
			<div>
				<xsl:if test="boolean($regclass/Selection/Item[@id=$codeNum]/Emphasis)='true'">
					<xsl:attribute name="class">
						<xsl:value-of select="'frame-note'"/>
					</xsl:attribute>
				</xsl:if>
				<p>
					<xsl:value-of select="$regclass/Selection/Item[@id=$codeNum]/Label[@type='preview']/Lang[@xml:lang=$lang]" />
					<xsl:if test="count(ns:RegulatoryClassificationComment/ns:Lang[@xml:lang=$lang])!=0">
						（<xsl:value-of select="ns:RegulatoryClassificationComment/ns:Lang[@xml:lang=$lang]" />）
					</xsl:if>
					<xsl:if test="count($regclass/Selection/Item[@id=$codeNum]/Comment)">
						<sup class="CommentRef">
							<xsl:attribute name="data-id"><xsl:value-of select="concat('REGFN_0', position())" /></xsl:attribute>
							<a>
								<xsl:attribute name="href">#<xsl:value-of select="@id" /></xsl:attribute>
								注<span class="CommentRefNum"></span>)
							</a>
						</sup>
					</xsl:if>
				</p>
				<xsl:if test="count($regclass/Selection/Item[@id=$codeNum]/Comment)">
					<span class="Comment" style="margin-left:15px;">
						<xsl:attribute name="data-id"><xsl:value-of select="concat('REGFN_0', position())" /></xsl:attribute>
						<a>
							<xsl:attribute name="name"><xsl:value-of select="@id" /></xsl:attribute>
							注<span class="CommentNum"></span>) <xsl:value-of select="$regclass/Selection/Item[@id=$codeNum]/Comment/Lang[@xml:lang=$lang]" />
						</a>
					</span>
				</xsl:if>
			</div>
		</xsl:for-each>
		<xsl:variable name="RegulatoryCount" select="count(ns:RegulatoryClassificationCodeAndNote)"/>
		<xsl:for-each select="ns:OtherRegulatoryClassification/ns:Lang[@xml:lang=$lang]">
			<div>
				<xsl:if test="contains(node()[position()=3],'赤枠')">
					<xsl:attribute name="class">
						<xsl:value-of select="'frame-note'"/>
					</xsl:attribute>
				</xsl:if>
				<xsl:choose>
					<xsl:when test ="string-length(normalize-space(node()[position()=3])) > 0">
						<xsl:variable name = "otherRegPosition" select="position()+$RegulatoryCount"/>
						<xsl:for-each select = "node()">
							<xsl:choose>
								<xsl:when test="position()=1">
									<p>
										<xsl:value-of select="." />
										<sup class="CommentRef">
											<xsl:attribute name="data-id">
												<xsl:value-of select="concat('REGFN_0', $otherRegPosition)" />
											</xsl:attribute>
											<u>
												注<span class="CommentRefNum"></span>)
											</u>
										</sup>
									</p>        	
								</xsl:when>
								<xsl:when test="position()=3">
									<span class="Comment" style="margin-left:15px;">
										<xsl:attribute name="data-id">
											<xsl:value-of select="concat('REGFN_0', $otherRegPosition)" />
										</xsl:attribute>
										<xsl:choose>
											<xsl:when test = "contains(.,'赤枠')">
												注<span class="CommentNum"></span>) 注意―<xsl:value-of select="concat(substring-before(.,'（赤枠'),substring-before(.,'(赤枠'))" />
											</xsl:when>
											<xsl:otherwise>
												注<span class="CommentNum"></span>) 注意―<xsl:value-of select="." />
											</xsl:otherwise>
										</xsl:choose>
									</span>
								</xsl:when>
							</xsl:choose>
						</xsl:for-each>
					</xsl:when>
					<xsl:otherwise>
						<p>
							<xsl:value-of select = "."/>
						</p>
					</xsl:otherwise>
				</xsl:choose>
			</div>
		</xsl:for-each>
	</xsl:template>

	<!-- 3. 組成・性状 -->
	<xsl:template match="ns:CompositionAndProperty">
		<!-- 3.1 製法の概要 -->
		<xsl:choose>
			<xsl:when test="$drugType='Vaccine' or $drugType='Antitoxin'">
				<xsl:apply-templates select="ns:OverviewOfRecipe" mode="Section-BLK">
					<xsl:with-param name="index" select="3.1" />
					<xsl:with-param name="level" select="2" />
					<xsl:with-param name="modifiedflg" select="'true'" />
					<xsl:with-param name="title" select="$label/OverviewOfRecipe" />
					<xsl:with-param name="mode" select="'content-TYPE'" />
				</xsl:apply-templates>
			</xsl:when>
		</xsl:choose>
		<!-- 3.2 組成 -->
		<xsl:apply-templates select="ns:Composition" mode="Section-BLK">
			<xsl:with-param name="index">
				<xsl:choose>
					<xsl:when test="$drugType='Vaccine' or $drugType='Antitoxin'">
						<xsl:value-of select="'3.2'" />
					</xsl:when>
					<xsl:otherwise>
						<xsl:value-of select="'3.1'" />
					</xsl:otherwise>
				</xsl:choose>
			</xsl:with-param>
			<xsl:with-param name="level" select="2" />
			<xsl:with-param name="title" select="$label/Composition" />
		</xsl:apply-templates>
		<!-- 3.3 製剤の性状 -->
		<xsl:apply-templates select="ns:Property" mode="Section-BLK">
			<xsl:with-param name="index">
				<xsl:choose>
					<xsl:when test="$drugType='Vaccine' or $drugType='Antitoxin'">
						<xsl:value-of select="'3.3'" />
					</xsl:when>
					<xsl:otherwise>
						<xsl:value-of select="'3.2'" />
					</xsl:otherwise>
				</xsl:choose>
			</xsl:with-param>
			<xsl:with-param name="level" select="2" />
			<xsl:with-param name="title" select="$label/Property" />
		</xsl:apply-templates>
	</xsl:template>

	<!-- ３.１ 組成 -->
	<xsl:template match="ns:Composition">
		<!-- 組成の概要 -->
		<xsl:apply-templates select="ns:OverviewOfComposition" mode="Section-BLK">
			<xsl:with-param name="title" select="'NONE'" />
			<xsl:with-param name="level" select="3" />
			<xsl:with-param name="modifiedflg" select="'true'" />
			<xsl:with-param name="mode" select="'content-TYPE'" />
		</xsl:apply-templates>
		<!-- 販売名ごとの組成 -->
		<xsl:for-each select="/ns:PackIns/ns:ApprovalEtc/ns:DetailBrandName">
			<xsl:variable name="id" select="@id" />
			<xsl:variable name="element" select="/ns:PackIns/ns:CompositionAndProperty/ns:Composition/ns:CompositionForBrand[@ref=$id]" />
			<xsl:variable name="brand" select="/ns:PackIns/ns:ApprovalEtc/ns:DetailBrandName[@id=$id]" />
			<xsl:choose>
				<xsl:when test="count(ns:ApprovalBrandName)!=0">
					<xsl:apply-templates select="$element" mode="Section-BLK">
						<xsl:with-param name="title" select="ns:ApprovalBrandName" />
						<xsl:with-param name="titleMode" select="'content-TYPE'" />
						<xsl:with-param name="level" select="3" />
						<xsl:with-param name="modifiedflg" select="'true'" />
						<!-- H29添付文書XML化対応 START -->
						<xsl:with-param name="id" select="concat('HDR_CompositionForBrand_', position())" />
						<!-- H29添付文書XML化対応 END -->
					</xsl:apply-templates>
				</xsl:when>
				<xsl:otherwise>
					<xsl:apply-templates select="$element" mode="Section-BLK">
						<xsl:with-param name="title" select="'（販売名）'" />
						<xsl:with-param name="level" select="3" />
						<xsl:with-param name="modifiedflg" select="'true'" />
					</xsl:apply-templates>
				</xsl:otherwise>
			</xsl:choose>
		</xsl:for-each>
		<!-- 組成に関する注釈 -->
		<xsl:apply-templates select="ns:CompositionComments" mode="Section-BLK">
			<xsl:with-param name="title" select="'NONE'" />
			<xsl:with-param name="level" select="3" />
			<xsl:with-param name="modifiedflg" select="'true'" />
			<xsl:with-param name="mode" select="'content-TYPE'" />
		</xsl:apply-templates>
	</xsl:template>

	<!-- 販売名毎の組成 -->
	<xsl:template match="ns:CompositionForBrand">
		<xsl:variable name="brandPosition" select="count(preceding-sibling::ns:CompositionForBrand)+1" />
		<!-- 構成ごとの組成 -->
		<xsl:for-each select="ns:CompositionForConstituentUnits">
			<!-- H29添付文書XML化対応 START -->
			<a>
				<xsl:attribute name="name">
					<xsl:value-of select="concat('HDR_CompositionForConstituentUnits_', $brandPosition, '_', position())" />
				</xsl:attribute>
			</a>
			<!-- H29添付文書XML化対応 END -->
			<xsl:apply-templates select="self::node()" mode="Section-BLK">
				<xsl:with-param name="level" select="4" />
				<xsl:with-param name="modifiedflg">
					<xsl:if test="count(ns:ConstituentUnits)!=0">true</xsl:if>
				</xsl:with-param>
				<xsl:with-param name="title" select="ns:ConstituentUnits" />
				<xsl:with-param name="titleMode" select="'content-TYPE'" />
			</xsl:apply-templates >
			<!-- 組成の構成に関する注釈 -->
			<xsl:apply-templates select="ns:CommentsForConstituentUnits" mode="Section-BLK">
				<xsl:with-param name="title" select="'NONE'" />
				<xsl:with-param name="mode" select="'content-TYPE'" />
				<xsl:with-param name="modifiedflg" select="'true'" />
			</xsl:apply-templates>
		</xsl:for-each>
	</xsl:template>

	<!-- 構成毎の組成 -->
	<xsl:template match="ns:CompositionForConstituentUnits">
		<!-- 組成テーブル -->
		<xsl:for-each select="ns:CompositionTable">
			<table class="CompositionAndProperty_table" border="1">
				<colgroup>
					<col width="200px"></col>
					<col width="300px"></col>
				</colgroup>
				<xsl:if test="count(ns:CompositionAndPropertyTblTitle/ns:Lang[@xml:lang=$lang])!=0" >
					<caption style="text-align:left">
						<xsl:apply-templates select="ns:CompositionAndPropertyTblTitle" mode="content-TYPE" />
					</caption>
				</xsl:if>
				<xsl:call-template name="ContainedAmount-ROW">
					<xsl:with-param name="element" select="ns:ContainedAmount" />
				</xsl:call-template>
				<xsl:call-template name="Additives-ROW">
					<xsl:with-param name="element" select="ns:Additives" />
				</xsl:call-template>
				<xsl:call-template name="OtherComposition-ROW">
					<xsl:with-param name="element" select="ns:OtherComposition" />
				</xsl:call-template>
				<xsl:call-template name="CompositionFoot-ROW">
					<xsl:with-param name="element" select="ns:CompositionAndPropertyTblFoot" />
				</xsl:call-template>
			</table>
		</xsl:for-each>
	</xsl:template>

	<!-- 有効成分行テンプレート -->
	<xsl:template name="ContainedAmount-ROW">
		<xsl:param name="element" select="EMPTY_NODE" />
		<xsl:if test="count($element)!=0">
			<xsl:for-each select="$element">
				<tr>
					<xsl:if test="position()=1">
						<th>
							<xsl:attribute name="rowspan">
								<xsl:value-of select="count($element)" />
							</xsl:attribute>
							<xsl:value-of select="$label/*[local-name()='ContainedAmount']" />
						</th>
					</xsl:if>
					<td>
						<xsl:if test="count(ns:ActiveIngredientName/ns:Lang[@xml:lang=$lang])!=0 or count(ns:ValueAndUnit/ns:Lang[@xml:lang=$lang])!=0">
							<xsl:apply-templates select="ns:ActiveIngredientName" mode="content-TYPE" />&#160;&#160;<xsl:value-of select="ns:ValueAndUnit" />
							<xsl:if test="count(ns:ActiveIngredientAdditionalInfo/ns:ActiveIngredientName/ns:Lang[@xml:lang=$lang])!=0 or count(ns:ActiveIngredientAdditionalInfo/ns:ValueAndUnit/ns:Lang[@xml:lang=$lang])!=0">
								<br/>
								（<xsl:apply-templates select="ns:ActiveIngredientAdditionalInfo/ns:ActiveIngredientName" mode="content-TYPE" />&#160;&#160;<xsl:value-of select="ns:ActiveIngredientAdditionalInfo/ns:ValueAndUnit" />）
							</xsl:if>
						</xsl:if>
					</td>
				</tr>
			</xsl:for-each>
		</xsl:if>
	</xsl:template>

	<!-- 添加剤行テンプレート -->
	<xsl:template name="Additives-ROW">
		<xsl:param name="element" select="EMPTY_NODE" />
		<xsl:choose>
			<!-- 添加剤リスト -->
			<xsl:when test="count($element/ns:ListOfAdditives)!=0">
				<tr>
					<th>
						<xsl:value-of select="$label/*[local-name()='Additives']" />
					</th>
					<td>
						<xsl:apply-templates select="$element/ns:ListOfAdditives" mode="content-TYPE" />
					</td>
				</tr>
			</xsl:when>
			<!-- 個別添加剤 -->
			<xsl:when test="count($element/ns:IndividualAdditives/ns:InfoIndividualAdditive)>0">
				<xsl:for-each select="$element/ns:IndividualAdditives/ns:InfoIndividualAdditive">
					<tr>
						<xsl:if test="position()=1">
							<th>
								<xsl:attribute name="rowspan">
									<xsl:value-of select="count($element/ns:IndividualAdditives/ns:InfoIndividualAdditive)" />
								</xsl:attribute>
								<xsl:value-of select="$label/*[local-name()='Additives']" />
							</th>
						</xsl:if>
						<td>
							<xsl:if test="count(ns:IndividualAdditive/ns:Lang[@xml:lang=$lang])!=0 or count(ns:ValueAndUnit/ns:Lang[@xml:lang=$lang])!=0">
								<xsl:apply-templates select="ns:IndividualAdditive" mode="content-TYPE" />&#160;&#160;<xsl:value-of select="ns:ValueAndUnit" />
							</xsl:if>
						</td>
					</tr>
				</xsl:for-each>
			</xsl:when>
		</xsl:choose>
	</xsl:template>

	<!-- 組成自由項目行テンプレート -->
	<xsl:template name="OtherComposition-ROW">
		<xsl:param name="element" select="EMPTY_NODE" />
		<xsl:if test="count($element)!=0">
			<!-- OtherPropertyごと -->
			<xsl:for-each select="$element">
				<xsl:variable name="node" select="self::node()" />
				<xsl:variable name="position" select="position()" />
				<xsl:for-each select="ns:Content">
					<tr>
						<!-- 分類名 -->
						<xsl:if test="position()=1">
							<th>
								<xsl:attribute name="rowspan">
									<xsl:value-of select="count($node/ns:Content)" />
								</xsl:attribute>
								<xsl:if test="count($node/ns:CategoryName/ns:Lang[@xml:lang=$lang])!=0">
									<xsl:apply-templates select="$node/ns:CategoryName" mode="content-TYPE" />
								</xsl:if>
							</th>
						</xsl:if>
						<!-- タイトル＆内容 -->
						<td>
							<xsl:if test="count(ns:ContentTitle/ns:Lang[@xml:lang=$lang])!=0 or count(ns:ContentDetail/ns:Lang[@xml:lang=$lang])!=0">
								<xsl:apply-templates select="ns:ContentTitle" mode="content-TYPE" />&#160;&#160;<xsl:apply-templates select="ns:ContentDetail" mode="content-TYPE" />
							</xsl:if>
						</td>
					</tr>
				</xsl:for-each>
				<!-- 分類名のみ -->
				<xsl:if test="count(ns:Content)=0 and count($node/ns:CategoryName)!=0">
					<tr>
						<th>
							<xsl:if test="count($node/ns:CategoryName/ns:Lang[@xml:lang=$lang])!=0">
								<xsl:apply-templates select="$node/ns:CategoryName" mode="content-TYPE" />
							</xsl:if>
						</th>
						<td></td>
					</tr>
				</xsl:if>
			</xsl:for-each>
		</xsl:if>
	</xsl:template>

	<!-- 組成フッタ行テンプレート -->
	<xsl:template name="CompositionFoot-ROW">
		<xsl:param name="element" select="EMPTY_NODE" />
		<xsl:if test="count($element/ns:Lang[@xml:lang=$lang])!=0">
			<tr class="tableFooter">
				<td colspan="99">
					<xsl:attribute name="style">text-align:<xsl:value-of select="$element/@align" />;</xsl:attribute>
					<xsl:apply-templates select="$element" mode="content-TYPE" />
				</td>
			</tr>
		</xsl:if>
	</xsl:template>

	<!-- ３.２ 製剤の性状 -->
	<xsl:template match="ns:Property">
		<!-- 性状の概要 -->
		<xsl:apply-templates select="ns:OverviewOfProperty" mode="Section-BLK">
			<xsl:with-param name="title" select="'NONE'" />
			<xsl:with-param name="level" select="3" />
			<xsl:with-param name="modifiedflg" select="'true'" />
			<xsl:with-param name="mode" select="'content-TYPE'" />
		</xsl:apply-templates>
		<!-- 販売名ごとの性状 -->
		<xsl:for-each select="/ns:PackIns/ns:ApprovalEtc/ns:DetailBrandName">
			<xsl:variable name="id" select="@id" />
			<xsl:variable name="element" select="/ns:PackIns/ns:CompositionAndProperty/ns:Property/ns:PropertyForBrand[@ref=$id]" />
			<xsl:variable name="brand" select="/ns:PackIns/ns:ApprovalEtc/ns:DetailBrandName[@id=$id]" />
			<xsl:choose>
				<xsl:when test="count(ns:ApprovalBrandName)!=0">
					<xsl:apply-templates select="$element" mode="Section-BLK">
						<xsl:with-param name="title" select="ns:ApprovalBrandName" />
						<xsl:with-param name="titleMode" select="'content-TYPE'" />
						<xsl:with-param name="level" select="3" />
						<xsl:with-param name="modifiedflg" select="'true'" />
						<!-- H29添付文書XML化対応 START -->
						<xsl:with-param name="id" select="concat('HDR_PropertyForBrand_', position())" />
						<!-- H29添付文書XML化対応 END -->
					</xsl:apply-templates>
				</xsl:when>
				<xsl:otherwise>
					<xsl:apply-templates select="$element" mode="Section-BLK">
						<xsl:with-param name="title" select="'（販売名）'" />
						<xsl:with-param name="level" select="3" />
						<xsl:with-param name="modifiedflg" select="'true'" />
					</xsl:apply-templates>
				</xsl:otherwise>
			</xsl:choose>
		</xsl:for-each>
	</xsl:template>

	<!-- 販売名毎の性状 -->
	<xsl:template match="ns:PropertyForBrand">
		<xsl:variable name="brandPosition" select="count(preceding-sibling::ns:PropertyForBrand)+1" />
		<!-- 構成ごとの性状 -->
		<xsl:for-each select="ns:PropertyForConstituentUnits">
			<!-- H29添付文書XML化対応 START -->
			<a>
				<xsl:attribute name="name">
					<xsl:value-of select="concat('HDR_PropertyForConstituentUnits_', $brandPosition, '_', position())" />
				</xsl:attribute>
			</a>
			<!-- H29添付文書XML化対応 END -->
			<xsl:apply-templates select="self::node()" mode="Section-BLK">
				<xsl:with-param name="level" select="4" />
				<xsl:with-param name="modifiedflg" select="'true'" />
				<xsl:with-param name="title" select="ns:ConstituentUnits" />
				<xsl:with-param name="titleMode" select="'content-TYPE'" />
			</xsl:apply-templates >
			<!-- 性状の構成に関する注釈 -->
			<xsl:apply-templates select="ns:CommentsForConstituentUnits" mode="Section-BLK">
				<xsl:with-param name="title" select="'NONE'" />
				<xsl:with-param name="mode" select="'content-TYPE'" />
				<xsl:with-param name="modifiedflg" select="'true'" />
			</xsl:apply-templates>
		</xsl:for-each>
	</xsl:template>

	<!-- 構成毎の性状 -->
	<xsl:template match="ns:PropertyForConstituentUnits">
		<!-- 性状テーブル -->
		<xsl:for-each select="ns:PropertyTable">
			<table class="CompositionAndProperty_table" border="1">
				<colgroup>
					<col width="100px"></col>
					<col width="100px"></col>
					<col width="200px"></col>
				</colgroup>
				<xsl:if test="count(ns:CompositionAndPropertyTblTitle/ns:Lang[@xml:lang=$lang])!=0" >
					<caption style="text-align:left">
						<xsl:apply-templates select="ns:CompositionAndPropertyTblTitle" mode="content-TYPE" />
					</caption>
				</xsl:if>
				<xsl:call-template name="Property-ROW">
					<xsl:with-param name="localname" select="'Formulation'" />
					<xsl:with-param name="element" select="ns:Formulation" />
				</xsl:call-template>
				<xsl:call-template name="Property-ROW">
					<xsl:with-param name="localname" select="'ColorTone'" />
					<xsl:with-param name="element" select="ns:ColorTone" />
				</xsl:call-template>
				<xsl:call-template name="Shape-ROW">
					<xsl:with-param name="localname" select="'Shape'" />
					<xsl:with-param name="element" select="ns:Shape" />
				</xsl:call-template>
				<xsl:call-template name="Size-ROW">
					<xsl:with-param name="localname" select="'Size'" />
					<xsl:with-param name="element" select="ns:Size" />
				</xsl:call-template>
				<xsl:call-template name="Property-ROW">
					<xsl:with-param name="localname" select="'SizeNumber'" />
					<xsl:with-param name="element" select="ns:SizeNumber" />
				</xsl:call-template>
				<xsl:call-template name="Property-ROW">
					<xsl:with-param name="localname" select="'Weight'" />
					<xsl:with-param name="element" select="ns:Weight" />
				</xsl:call-template>
				<xsl:call-template name="Property-ROW">
					<xsl:with-param name="localname" select="'IdCode'" />
					<xsl:with-param name="element" select="ns:IdCode" />
				</xsl:call-template>
				<xsl:call-template name="Property-ROW">
					<xsl:with-param name="localname" select="'pH'" />
					<xsl:with-param name="element" select="ns:pH" />
				</xsl:call-template>
				<xsl:call-template name="Property-ROW">
					<xsl:with-param name="localname" select="'OsmoticRatio'" />
					<xsl:with-param name="element" select="ns:OsmoticRatio" />
				</xsl:call-template>
				<xsl:call-template name="Property-ROW">
					<xsl:with-param name="localname" select="'Odor'" />
					<xsl:with-param name="element" select="ns:Odor" />
				</xsl:call-template>
				<xsl:call-template name="Property-ROW">
					<xsl:with-param name="localname" select="'Taste'" />
					<xsl:with-param name="element" select="ns:Taste" />
				</xsl:call-template>
				<xsl:call-template name="OtherProperty-ROW">
					<xsl:with-param name="element" select="ns:OtherProperty" />
				</xsl:call-template>
				<xsl:call-template name="PropertyFoot-ROW">
					<xsl:with-param name="element" select="ns:CompositionAndPropertyTblFoot" />
				</xsl:call-template>
			</table>
		</xsl:for-each>
	</xsl:template>

	<!-- 性状行テンプレート -->
	<xsl:template name="Property-ROW">
		<xsl:param name="localname" select="''" />
		<xsl:param name="sublocalname" select="''" />
		<xsl:param name="element" select="EMPTY_NODE" />
		<xsl:param name="colspan" select="'2'" />
		<xsl:param name="rowspan" select="''" />
		<xsl:if test="count($element)!=0">
			<tr>
				<th>
					<xsl:attribute name="colspan"><xsl:value-of select="$colspan" /></xsl:attribute>
					<xsl:if test="$rowspan!='' and count(preceding-sibling)=0">
						<xsl:attribute name="rowspan"><xsl:value-of select="$rowspan" /></xsl:attribute>
					</xsl:if>
					<xsl:value-of select="$label/*[local-name()=$localname]" />
				</th>
				<xsl:if test="$colspan!='2'">
					<th>
						<xsl:value-of select="$label/*[local-name()=$sublocalname]" />
					</th>
				</xsl:if>
				<td>
					<xsl:if test="count($element/ns:Lang[@xml:lang=$lang])!=0">
						<xsl:apply-templates select="$element" mode="content-TYPE" />
					</xsl:if>
				</td>
			</tr>
		</xsl:if>
	</xsl:template>

	<!-- 外形行テンプレート -->
	<xsl:template name="Shape-ROW">
		<xsl:param name="localname" select="''" />
		<xsl:param name="element" select="EMPTY_NODE" />
		<xsl:variable name="Shapes" select="count($element/*)" />
		<xsl:variable name="ShapeTitles" select="count($element//ns:ShapeTitle)" />
		<xsl:for-each select="$element/ns:ShapeFront|$element/ns:ShapeBack|$element/ns:ShapeSide|$element/ns:OtherShape">
			<!-- H29添付文書XML化対応 START -->
			<xsl:variable name="childname" select="substring-after(name(),'')" />
			<!-- H29添付文書XML化対応 END -->
			<tr>
				<xsl:if test="position()=1">
					<th>
						<xsl:if test="$childname='OtherShape' and $ShapeTitles=0">
							<xsl:attribute name="colspan">2</xsl:attribute>
						</xsl:if>
						<xsl:attribute name="rowspan"><xsl:value-of select="$Shapes" /></xsl:attribute>
						<xsl:value-of select="$label/*[local-name()=$localname]" />
					</th>
				</xsl:if>
				<xsl:if test="$childname!='OtherShape' or $ShapeTitles!=0">
					<th>
						<xsl:choose>
							<xsl:when test="$childname='OtherShape' and count(ns:ShapeTitle)!=0">
								<xsl:apply-templates select="ns:ShapeTitle" mode="content-TYPE" />
							</xsl:when>
							<xsl:otherwise>
								<xsl:value-of select="$label/*[local-name()=$childname]" />
							</xsl:otherwise>
						</xsl:choose>
					</th>
				</xsl:if>
				<td>
					<xsl:choose>
						<xsl:when test="$childname='OtherShape' and count(ns:ShapeDetail/ns:Lang[@xml:lang=$lang])!=0">
							<xsl:apply-templates select="ns:ShapeDetail" mode="content-TYPE" />
						</xsl:when>
						<xsl:when test="count(ns:Lang[@xml:lang=$lang])!=0">
							<xsl:apply-templates select="self::node()" mode="content-TYPE" />
						</xsl:when>
					</xsl:choose>
				</td>
			</tr>
		</xsl:for-each>
	</xsl:template>

	<!-- 大きさ行テンプレート -->
	<xsl:template name="Size-ROW">
		<xsl:param name="localname" select="''" />
		<xsl:param name="element" select="EMPTY_NODE" />
		<xsl:variable name="Sizes" select="count($element/*)" />
		<xsl:variable name="SizeTitles" select="count($element//ns:SizeTitle)" />
		<xsl:for-each select="$element/ns:SizeDiameter|$element/ns:SizeLongDiameter|$element/ns:SizeShortDiameter|$element/ns:SizeTotalLength|$element/ns:SizeThickness|$element/ns:SizeArea|$element/ns:OtherSize">
			<!-- H29添付文書XML化対応 START -->
			<xsl:variable name="childname" select="substring-after(name(),'')" />
			<!-- H29添付文書XML化対応 END -->
			<tr>
				<xsl:if test="position()=1">
					<th>
						<xsl:if test="$childname='OtherSize' and $SizeTitles=0">
							<xsl:attribute name="colspan">2</xsl:attribute>
						</xsl:if>
						<xsl:attribute name="rowspan"><xsl:value-of select="$Sizes" /></xsl:attribute>
						<xsl:value-of select="$label/*[local-name()=$localname]" />
					</th>
				</xsl:if>
				<xsl:if test="$childname!='OtherSize' or $SizeTitles!=0">
					<th>
						<xsl:choose>
							<xsl:when test="$childname='OtherSize' and count(ns:SizeTitle)!=0">
								<xsl:apply-templates select="ns:SizeTitle" mode="content-TYPE" />
							</xsl:when>
							<xsl:otherwise>
								<xsl:value-of select="$label/*[local-name()=$childname]" />
							</xsl:otherwise>
						</xsl:choose>
					</th>
				</xsl:if>
				<td>
					<xsl:choose>
						<xsl:when test="$childname='OtherSize' and count(ns:SizeDetail/ns:Lang[@xml:lang=$lang])!=0">
							<xsl:apply-templates select="ns:SizeDetail" mode="content-TYPE" />
						</xsl:when>
						<xsl:when test="count(ns:Lang[@xml:lang=$lang])!=0">
							<xsl:apply-templates select="self::node()" mode="content-TYPE" />
						</xsl:when>
					</xsl:choose>
				</td>
			</tr>
		</xsl:for-each>
	</xsl:template>

	<!--	性状自由項目行テンプレート -->
	<xsl:template name="OtherProperty-ROW">
		<xsl:param name="element" select="EMPTY_NODE" />
		<xsl:for-each select="$element">
			<xsl:variable name="Contents" select="count(ns:Content)" />
			<xsl:variable name="ContentTitles" select="count(ns:Content/ns:ContentTitle)" />
				<xsl:for-each select="ns:Content">
					<tr>
						<xsl:if test="position()=1">
							<th>
								<xsl:if test="$ContentTitles=0">
									<xsl:attribute name="colspan">2</xsl:attribute>
								</xsl:if>
								<xsl:attribute name="rowspan"><xsl:value-of select="$Contents" /></xsl:attribute>
								<xsl:if test="count(../ns:CategoryName/ns:Lang[@xml:lang=$lang])!=0">
									<xsl:apply-templates select="../ns:CategoryName" mode="content-TYPE" />
								</xsl:if>
							</th>
						</xsl:if>
						<xsl:if test="$ContentTitles!=0">
							<th>
								<xsl:if test="count(ns:ContentTitle)!=0">
									<xsl:apply-templates select="ns:ContentTitle" mode="content-TYPE" />
								</xsl:if>
							</th>
						</xsl:if>
						<td>
							<xsl:if test="count(ns:ContentDetail/ns:Lang[@xml:lang=$lang])!=0">
								<xsl:apply-templates select="ns:ContentDetail" mode="content-TYPE" />
							</xsl:if>
						</td>
					</tr>
				</xsl:for-each>
				<!--	分類名のみ -->
				<xsl:if test="count(ns:Content)=0 and count(ns:CategoryName)!=0">
					<tr>
						<th>
							<xsl:attribute name="colspan">2</xsl:attribute>
							<xsl:attribute name="rowspan">1</xsl:attribute>
							<xsl:if test="count(ns:CategoryName/ns:Lang[@xml:lang=$lang])!=0">
								<xsl:apply-templates select="ns:CategoryName" mode="content-TYPE" />
							</xsl:if>
						</th>
						<td></td>
					</tr>
				</xsl:if>
		</xsl:for-each>
	</xsl:template>

	<!-- 性状フッタ行テンプレート -->
	<xsl:template name="PropertyFoot-ROW">
		<xsl:param name="element" select="EMPTY_NODE" />
		<xsl:if test="count($element/ns:Lang[@xml:lang=$lang])!=0">
			<tr class="tableFooter">
				<td colspan="99">
					<xsl:attribute name="style">text-align:<xsl:value-of select="$element/@align" />;</xsl:attribute>
					<xsl:apply-templates select="$element" mode="content-TYPE" />
				</td>
			</tr>
		</xsl:if>
	</xsl:template>

	<!-- 6. 用法及び用量 -->
	<xsl:template match="ns:InfoDoseAdmin">
		<xsl:apply-templates select="ns:DoseAdmin" mode="VariousForm-TYPE">
			<xsl:with-param name="index" select="6" />
			<xsl:with-param name="level" select="1" />
		</xsl:apply-templates>
		<xsl:apply-templates select="ns:OtherRelatedMatters" mode="Section-BLK">
			<xsl:with-param name="title">
				<xsl:variable name="id" select="@wordingPatternOfDoseAdmin" />
				<xsl:value-of select="$label/OtherRelatedMatters/Item[@id=$id]" />
			</xsl:with-param>
			<xsl:with-param name="mode" select="'VariousForm-TYPE'" />
		</xsl:apply-templates>
	</xsl:template>


	<!-- 9. 特定の背景を有する患者に関する注意 -->
	<xsl:template match="ns:UseInSpecificPopulations">
		<!-- 9.1 合併症・既往症等のある患者 -->
		<xsl:apply-templates select="ns:UseInPatientsWithComplicationsOrHistoryOfDiseasesEtc" mode="Section-BLK">
			<xsl:with-param name="title">
				<xsl:value-of select="$label/UseInPatientsWithComplicationsOrHistoryOfDiseasesEtc/Item[@id=$drugType]" />
			</xsl:with-param>
			<xsl:with-param name="index" select="9.1" />
			<xsl:with-param name="level" select="2" />
			<xsl:with-param name="mode" select="'VariousForm-TYPE'" />
		</xsl:apply-templates>
		<!-- 9.2 腎機能障害患者 -->
		<xsl:apply-templates select="ns:PatientsWithRenalImpairment" mode="Section-BLK">
			<xsl:with-param name="title">
				<xsl:value-of select="$label/PatientsWithRenalImpairment/Item[@id=$drugType]" />
			</xsl:with-param>
			<xsl:with-param name="index" select="9.2" />
			<xsl:with-param name="level" select="2" />
			<xsl:with-param name="mode" select="'VariousForm-TYPE'" />
		</xsl:apply-templates>
		<!-- 9.3 肝機能障害患者 -->
		<xsl:apply-templates select="ns:PatientsWithHepaticImpairment" mode="Section-BLK">
			<xsl:with-param name="title">
				<xsl:value-of select="$label/PatientsWithHepaticImpairment/Item[@id=$drugType]" />
			</xsl:with-param>
			<xsl:with-param name="index" select="9.3" />
			<xsl:with-param name="level" select="2" />
			<xsl:with-param name="mode" select="'VariousForm-TYPE'" />
		</xsl:apply-templates>
		<!-- 9.4 生殖能を有する者 -->
		<xsl:apply-templates select="ns:MalesAndFemalesOfReproductivePotential" mode="Section-BLK">
			<xsl:with-param name="index" select="9.4" />
			<xsl:with-param name="level" select="2" />
			<xsl:with-param name="mode" select="'VariousForm-TYPE'" />
		</xsl:apply-templates>
		<!-- 9.5 妊婦 -->
		<xsl:apply-templates select="ns:UseInPregnant" mode="Section-BLK">
			<xsl:with-param name="index" select="9.5" />
			<xsl:with-param name="level" select="2" />
			<xsl:with-param name="mode" select="'VariousForm-TYPE'" />
		</xsl:apply-templates>
		<!-- 9.6 授乳婦 -->
		<xsl:apply-templates select="ns:UseInNursing" mode="Section-BLK">
			<xsl:with-param name="index" select="9.6" />
			<xsl:with-param name="level" select="2" />
			<xsl:with-param name="mode" select="'VariousForm-TYPE'" />
		</xsl:apply-templates>
		<!-- 9.7 小児等 -->
		<xsl:apply-templates select="ns:PediatricUse" mode="Section-BLK">
			<xsl:with-param name="index" select="9.7" />
			<xsl:with-param name="level" select="2" />
			<xsl:with-param name="mode" select="'VariousForm-TYPE'" />
		</xsl:apply-templates>
		<!-- 9.8 高齢者 -->
		<xsl:apply-templates select="ns:UseInTheElderly" mode="Section-BLK">
			<xsl:with-param name="index" select="9.8" />
			<xsl:with-param name="level" select="2" />
			<xsl:with-param name="mode" select="'VariousForm-TYPE'" />
		</xsl:apply-templates>
	</xsl:template>


	<!-- 10. 相互作用 -->
	<xsl:template match="ns:Interactions">
		<!-- 相互作用の概略 -->
		<ul class="HeaderDetailList" style="list-style-type:none;position:relative; left:-15px;">
			<xsl:apply-templates select="ns:SummaryOfCombination" mode="HeaderDetailList-TYPE">
				<xsl:with-param name="index" select="'10'" />
			</xsl:apply-templates>
		</ul>
		<!-- 10.1 併用禁忌(併用しないこと) -->
		<xsl:apply-templates select="ns:ContraIndicatedCombinations[count(./*[not(contains(local-name(),'Obsolete-SGML-'))])>0]" mode="Section-BLK">
			<xsl:with-param name="index" select="10.1" />
			<xsl:with-param name="level" select="2" />
		</xsl:apply-templates>
		<!-- 10.2 併用注意(併用に注意すること) -->
		<xsl:apply-templates select="ns:PrecautionsForCombinations[count(./*[not(contains(local-name(),'Obsolete-SGML-'))])>0]" mode="Section-BLK">
			<xsl:with-param name="index" select="10.2" />
			<xsl:with-param name="level" select="2" />
		</xsl:apply-templates>
	</xsl:template>

	<!-- 併用禁忌 -->
	<xsl:template match="ns:ContraIndicatedCombinations">
		<xsl:for-each select="ns:ContraIndicatedCombination">
      <div class="RepeatingElements">
			  <xsl:apply-templates select="ns:Instructions" mode="VariousForm-TYPE" />
		<xsl:apply-templates select="ns:ContraIndication" mode="InteractionsTable" />
		<xsl:apply-templates select="ns:ExplanatoryNotesForContraIndication" mode="content-TYPE" />
      </div>
		</xsl:for-each>
	</xsl:template>

	<!-- 併用注意 -->
	<xsl:template match="ns:PrecautionsForCombinations">
		<xsl:for-each select="ns:PrecautionsForCombination">
      <div class="RepeatingElements">
  			<xsl:apply-templates select="ns:Instructions" mode="VariousForm-TYPE" />
		<xsl:apply-templates select="ns:PrecautionsForCombi" mode="InteractionsTable" />
		<xsl:apply-templates select="ns:ExplanatoryNotesForPrecautions" mode="content-TYPE" />
      </div>
		</xsl:for-each>
	</xsl:template>

	<!-- 併用禁忌・併用注意のテーブル -->
	<xsl:template match="ns:*" mode="InteractionsTable">
		<table border="1">
			<xsl:choose>
				<xsl:when test="local-name(self::node())='ContraIndication'">
					<xsl:attribute name="class">ContraIndication_table</xsl:attribute>
				</xsl:when>
				<xsl:when test="local-name(self::node())='PrecautionsForCombi'">
					<xsl:attribute name="class">PrecautionsForCombi_table</xsl:attribute>
				</xsl:when>
			</xsl:choose>
			<xsl:attribute name="style">
				width:<xsl:value-of select="ns:WidthDefinition/@totalWidth" />
			</xsl:attribute>
			<thead>
				<tr>
					<th>
						<xsl:attribute name="style">
							width:<xsl:value-of select="ns:WidthDefinition/ns:Col[position()=1]/@width" />
						</xsl:attribute>
						<xsl:value-of select="$label/*[local-name()='Names']" />
					</th>
					<th>
						<xsl:attribute name="style">
							width:<xsl:value-of select="ns:WidthDefinition/ns:Col[position()=2]/@width" />
						</xsl:attribute>
						<xsl:value-of select="$label/*[local-name()='ClinSymptomsAndMeasures']" />
					</th>
					<th>
						<xsl:attribute name="style">
							width:<xsl:value-of select="ns:WidthDefinition/ns:Col[position()=3]/@width" />
						</xsl:attribute>
						<xsl:value-of select="$label/*[local-name()='MechanismAndRiskFactors']" />
					</th>
				</tr>
			</thead>
			<tbody>
				<xsl:apply-templates select="ns:Drug" />
			</tbody>
		</table>
	</xsl:template>

	<!-- 薬品 -->
	<xsl:template match="ns:Drug">
		<tr>
			<xsl:choose>
				<xsl:when test="count(ns:DrugName)!=0">
					<td>
						<xsl:apply-templates select="ns:DrugName" mode="VariousForm-TYPE">
							<xsl:with-param name="index" select="'1'" />
							<xsl:with-param name="level" select="'3'" />
						</xsl:apply-templates>
					</td>
				</xsl:when>
				<xsl:otherwise>
					<td></td>
				</xsl:otherwise>
			</xsl:choose>
			<xsl:choose>
				<xsl:when test="count(ns:ClinSymptomsAndMeasures)!=0">
					<td>
						<xsl:apply-templates select="ns:ClinSymptomsAndMeasures" mode="VariousForm-TYPE" >
							<xsl:with-param name="index" select="'1'" />
							<xsl:with-param name="level" select="'3'" />
						</xsl:apply-templates>
					</td>
				</xsl:when>
				<xsl:otherwise>
					<td></td>
				</xsl:otherwise>
			</xsl:choose>
			<xsl:choose>
				<xsl:when test="count(ns:MechanismAndRiskFactors)!=0">
					<td>
						<xsl:apply-templates select="ns:MechanismAndRiskFactors" mode="VariousForm-TYPE" >
							<xsl:with-param name="index" select="'1'" />
							<xsl:with-param name="level" select="'3'" />
						</xsl:apply-templates>
					</td>
				</xsl:when>
				<xsl:otherwise>
					<td></td>
				</xsl:otherwise>
			</xsl:choose>
		</tr>
	</xsl:template>


	<!-- 11. 副作用 -->
	<xsl:template match="ns:AdverseEvents">
		<!-- 副作用の共通の注意 -->
		<xsl:apply-templates select="ns:CommonPrecautionsForAdverse" mode="content-TYPE"/>
		<!-- 11.1 重大な副作用 -->
		<xsl:apply-templates select="ns:SeriousAdverseEvents" mode="Section-BLK">
			<xsl:with-param name="title">
				<xsl:value-of select="$label/SeriousAdverseEvents/Item[@id=$drugType]" />
			</xsl:with-param>
			<xsl:with-param name="index" select="11.1" />
			<xsl:with-param name="level" select="2" />
		</xsl:apply-templates>
		<!-- 11.2 その他の副作用 -->
		<xsl:apply-templates select="ns:OtherAdverseEvents" mode="Section-BLK">
			<xsl:with-param name="title">
				<xsl:value-of select="$label/OtherAdverseEvents/Item[@id=$drugType]" />
			</xsl:with-param>
			<xsl:with-param name="index" select="11.2" />
			<xsl:with-param name="level" select="2" />
		</xsl:apply-templates>
		<!-- 副作用の共通の注釈 -->
		<xsl:apply-templates select="ns:CommonExplanatoryNotesForAdverse" mode="content-TYPE"/>
	</xsl:template>

	<!-- 重大な副作用 -->
	<xsl:template match="ns:SeriousAdverseEvents">
		<xsl:apply-templates select="ns:Instructions" mode="VariousForm-TYPE"/>
		<xsl:apply-templates select="ns:SeriousAdverse" mode="VariousForm-TYPE">
			<xsl:with-param name="index" select="11.1" />
			<xsl:with-param name="level" select="2" />
		</xsl:apply-templates>
		<xsl:apply-templates select="ns:ExplanatoryNotesForSeriousAdverse" mode="content-TYPE"/>
	</xsl:template>

	<!-- その他の副作用 -->
	<xsl:template match="ns:OtherAdverseEvents">
		<xsl:for-each select="ns:OtherAdverseEvent">
      <div class="RepeatingElements">
			<xsl:apply-templates select="ns:Instructions" mode="VariousForm-TYPE"/>
			<xsl:apply-templates select="ns:OtherAdverse" />
			<xsl:apply-templates select="ns:ExplanatoryNotesForOtherAdverse" mode="content-TYPE"/>
      </div>
		</xsl:for-each>
	</xsl:template>

	<!-- その他の副作用 -->
	<xsl:template match="ns:OtherAdverse">
		<table border="1">
			<xsl:attribute name="style">
				width:<xsl:value-of select="ns:WidthDefinition/@totalWidth" />;margin-bottom:10px;
			</xsl:attribute>
			<xsl:attribute name="class">OtherAdverse_table</xsl:attribute>
			<thead>
				<tr>
					<th>
						<xsl:attribute name="style">
							width:<xsl:value-of select="ns:WidthDefinition/ns:Col[position()=1]/@width" />
						</xsl:attribute>
					</th>
					<xsl:for-each select="ns:FrequencyDefinition/ns:Frequency">
						<xsl:variable name="position" select="position()" />
						<th>
							<xsl:attribute name="style">
								width:<xsl:value-of select="../../ns:WidthDefinition/ns:Col[position()=$position+1]/@width" />
							</xsl:attribute>
							<xsl:apply-templates select="self::node()" mode="VariousForm-TYPE" >
								<xsl:with-param name="index" select="'1'" />
								<xsl:with-param name="level" select="'3'" />
							</xsl:apply-templates>
						</th>
					</xsl:for-each>
				</tr>
			</thead>
			<tbody>
				<xsl:for-each select="ns:CategoryDefinition/ns:Category">
					<xsl:variable name="category" select="@id" />
					<tr>
						<th>
							<xsl:apply-templates select="self::node()" mode="VariousForm-TYPE" >
								<xsl:with-param name="index" select="'1'" />
								<xsl:with-param name="level" select="'3'" />
							</xsl:apply-templates>
						</th>
						<xsl:for-each select="../../ns:FrequencyDefinition/ns:Frequency">
							<xsl:variable name="frequency" select="@id" />
							<td>
								<xsl:apply-templates select="../../ns:AdverseReactions/ns:AdverseReactionDescription[@categoryRef=$category][@frequencyRef=$frequency]" mode="VariousForm-TYPE" >
									<xsl:with-param name="index" select="'1'" />
									<xsl:with-param name="level" select="'3'" />
								</xsl:apply-templates>
							</td>
						</xsl:for-each>
					</tr>
				</xsl:for-each>
			</tbody>
		</table>
	</xsl:template>


	<!-- 14. 適用上の注意 -->
	<xsl:template match="ns:PrecautionsForApplication">
		<xsl:apply-templates select="self::node()" mode="OtherInformation-BLK">
			<xsl:with-param name="index" select="14" />
		</xsl:apply-templates>
	</xsl:template>


	<!-- 15. その他の注意 -->
	<xsl:template match="ns:OtherPrecautions">
		<!-- 15.1 臨床使用に基づく情報 -->
		<xsl:apply-templates select="ns:InformationBasedOnClinicalUse" mode="Section-BLK">
			<xsl:with-param name="index" select="15.1" />
			<xsl:with-param name="level" select="2" />
			<xsl:with-param name="mode" select="'VariousForm-TYPE'" />
		</xsl:apply-templates>
		<!-- 15.2 非臨床試験に基づく情報 -->
		<xsl:apply-templates select="ns:InformationBasedOnNonclinicalStudies" mode="Section-BLK">
			<xsl:with-param name="index" select="15.2" />
			<xsl:with-param name="level" select="2" />
			<xsl:with-param name="mode" select="'VariousForm-TYPE'" />
		</xsl:apply-templates>
		<!-- その他 -->
		<xsl:apply-templates select="self::node()" mode="OtherInformation-BLK">
			<xsl:with-param name="index" select="15" />
			<xsl:with-param name="level" select="2" />
			<xsl:with-param name="startIndex" select="3" />
		</xsl:apply-templates>
	</xsl:template>


	<!-- 16. 薬物動態 -->
	<xsl:template match="ns:Pharmacokinetics">
		<!-- 16.1 血中濃度 -->
		<xsl:apply-templates select="ns:BloodLevel" mode="Section-BLK">
			<xsl:with-param name="index" select="16.1" />
			<xsl:with-param name="level" select="2" />
			<xsl:with-param name="mode" select="'VariousForm-TYPE'" />
		</xsl:apply-templates>
		<!-- 16.2 吸収 -->
		<xsl:apply-templates select="ns:Absorption" mode="Section-BLK">
			<xsl:with-param name="index" select="16.2" />
			<xsl:with-param name="level" select="2" />
			<xsl:with-param name="mode" select="'VariousForm-TYPE'" />
		</xsl:apply-templates>
		<!-- 16.3 分布 -->
		<xsl:apply-templates select="ns:Distribution" mode="Section-BLK">
			<xsl:with-param name="index" select="16.3" />
			<xsl:with-param name="level" select="2" />
			<xsl:with-param name="mode" select="'VariousForm-TYPE'" />
		</xsl:apply-templates>
		<!-- 16.4 代謝 -->
		<xsl:apply-templates select="ns:Metabolism" mode="Section-BLK">
			<xsl:with-param name="index" select="16.4" />
			<xsl:with-param name="level" select="2" />
			<xsl:with-param name="mode" select="'VariousForm-TYPE'" />
		</xsl:apply-templates>
		<!-- 16.5 排泄 -->
		<xsl:apply-templates select="ns:Excretion" mode="Section-BLK">
			<xsl:with-param name="index" select="16.5" />
			<xsl:with-param name="level" select="2" />
			<xsl:with-param name="mode" select="'VariousForm-TYPE'" />
		</xsl:apply-templates>
		<!-- 16.6 特定の背景を有する患者 -->
		<xsl:apply-templates select="ns:SpecificPopulation" mode="Section-BLK">
			<xsl:with-param name="title">
				<xsl:value-of select="$label/SpecificPopulation/Item[@id=$drugType]" />
			</xsl:with-param>
			<xsl:with-param name="index" select="16.6" />
			<xsl:with-param name="level" select="2" />
			<xsl:with-param name="mode" select="'VariousForm-TYPE'" />
		</xsl:apply-templates>
		<!-- 16.7 薬物相互作用 -->
		<xsl:apply-templates select="ns:DrugAndDrugInteractions" mode="Section-BLK">
			<xsl:with-param name="index" select="16.7" />
			<xsl:with-param name="level" select="2" />
			<xsl:with-param name="mode" select="'VariousForm-TYPE'" />
		</xsl:apply-templates>
		<!-- 16.8 その他 -->
		<xsl:apply-templates select="ns:PharmacokineticsEtc" mode="Section-BLK">
			<xsl:with-param name="index" select="16.8" />
			<xsl:with-param name="level" select="2" />
			<xsl:with-param name="mode" select="'VariousForm-TYPE'" />
		</xsl:apply-templates>
	</xsl:template>


	<!-- 17. 臨床成績 -->
	<xsl:template match="ns:ResultsOfClinicalTrials">
		<!-- 17.1 有効性及び安全性に関する試験 -->
		<xsl:apply-templates select="ns:EfficacyAndSafety" mode="Section-BLK">
			<xsl:with-param name="index" select="17.1" />
			<xsl:with-param name="level" select="2" />
			<xsl:with-param name="mode" select="'VariousForm-TYPE'" />
		</xsl:apply-templates>
		<!-- 17.2 製造販売後調査等 -->
		<xsl:apply-templates select="ns:PostMarketingSurveylancesEtc" mode="Section-BLK">
			<xsl:with-param name="index" select="17.2" />
			<xsl:with-param name="level" select="2" />
			<xsl:with-param name="mode" select="'VariousForm-TYPE'" />
		</xsl:apply-templates>
		<!-- 17.3 その他 -->
		<xsl:apply-templates select="ns:ResultsOfClinicalTrialsEtc" mode="Section-BLK">
			<xsl:with-param name="index" select="17.3" />
			<xsl:with-param name="level" select="2" />
			<xsl:with-param name="mode" select="'VariousForm-TYPE'" />
		</xsl:apply-templates>
	</xsl:template>


	<!-- 18. 薬効薬理 -->
	<xsl:template match="ns:EfficacyPharmacology">
		<!-- 18.1 作用機序 -->
		<xsl:apply-templates select="ns:MechanismOfAction" mode="Section-BLK">
			<xsl:with-param name="index" select="18.1" />
			<xsl:with-param name="level" select="2" />
			<xsl:with-param name="mode" select="'VariousForm-TYPE'" />
		</xsl:apply-templates>
		<!-- 18.1 測定法 -->
		<xsl:apply-templates select="ns:MeasurementMethod" mode="Section-BLK">
			<xsl:with-param name="index" select="18.1" />
			<xsl:with-param name="level" select="2" />
			<xsl:with-param name="mode" select="'VariousForm-TYPE'" />
		</xsl:apply-templates>
		<!-- 18.2 その他 -->
		<xsl:apply-templates select="self::node()" mode="OtherInformation-BLK">
			<xsl:with-param name="index" select="18" />
			<xsl:with-param name="startIndex" select="2" />
		</xsl:apply-templates>
	</xsl:template>


	<!-- 19. 有効成分に関する理化学的知見 -->
	<xsl:template match="ns:PhyschemOfActIngredients">
		<xsl:for-each select="ns:PhyschemOfActIngredientsSection">
			<div>
				<xsl:attribute name="id">PhyschemOfActIngredientsSection_<xsl:value-of select="position()" /></xsl:attribute>
				<xsl:apply-templates select="self::node()" mode="Section-BLK">
					<xsl:with-param name="title" select="ns:PhyschemOfActIngredientsSectionTitle" />
					<xsl:with-param name="titleMode" select="'content-TYPE'" />
					<xsl:with-param name="modifiedflg" select="'true'" />
				</xsl:apply-templates>
			</div>
		</xsl:for-each>
	</xsl:template>

	<!-- 有効成分に関する理化学的知見のセクション -->
	<xsl:template match="ns:PhyschemOfActIngredientsSection">
		<xsl:apply-templates select="ns:GeneralName" mode="Section-BLK">
			<xsl:with-param name="title" select="$label/GenericName" />
			<xsl:with-param name="mode" select="'VariousForm-TYPE'" />
			<xsl:with-param name="modifiedflg" select="'true'" />
		</xsl:apply-templates>
		<xsl:apply-templates select="ns:ChemicalName" mode="Section-BLK">
			<xsl:with-param name="mode" select="'VariousForm-TYPE'" />
			<xsl:with-param name="modifiedflg" select="'true'" />
		</xsl:apply-templates>
		<xsl:apply-templates select="ns:MolecularFormula" mode="Section-BLK">
			<xsl:with-param name="mode" select="'VariousForm-TYPE'" />
			<xsl:with-param name="modifiedflg" select="'true'" />
		</xsl:apply-templates>
		<xsl:apply-templates select="ns:MolecularWeight" mode="Section-BLK">
			<xsl:with-param name="mode" select="'VariousForm-TYPE'" />
			<xsl:with-param name="modifiedflg" select="'true'" />
		</xsl:apply-templates>
		<xsl:apply-templates select="ns:DescriptionOfActiveIngredients" mode="Section-BLK">
			<xsl:with-param name="mode" select="'VariousForm-TYPE'" />
							<xsl:with-param name="modifiedflg" select="'true'" />
		</xsl:apply-templates>
		<xsl:apply-templates select="ns:StructuralFormula" mode="Section-BLK">
			<xsl:with-param name="mode" select="'VariousForm-TYPE'" />
			<xsl:with-param name="modifiedflg" select="'true'" />
		</xsl:apply-templates>
		<xsl:apply-templates select="ns:MeltingPoint" mode="Section-BLK">
			<xsl:with-param name="mode" select="'VariousForm-TYPE'" />
			<xsl:with-param name="modifiedflg" select="'true'" />
		</xsl:apply-templates>
		<xsl:apply-templates select="ns:PartitionCoefficient" mode="Section-BLK">
			<xsl:with-param name="mode" select="'VariousForm-TYPE'" />
			<xsl:with-param name="modifiedflg" select="'true'" />
		</xsl:apply-templates>
		<xsl:apply-templates select="ns:Nature" mode="Section-BLK">
			<xsl:with-param name="mode" select="'VariousForm-TYPE'" />
			<xsl:with-param name="modifiedflg" select="'true'" />
		</xsl:apply-templates>
		<xsl:apply-templates select="ns:NucleophysicalProperties" mode="Section-BLK">
			<xsl:with-param name="mode" select="'VariousForm-TYPE'" />
			<xsl:with-param name="modifiedflg" select="'true'" />
		</xsl:apply-templates>
		<xsl:apply-templates select="self::node()" mode="OtherInformation-BLK">
			<xsl:with-param name="level" select="'99'" />
		</xsl:apply-templates>
	</xsl:template>

	<!-- 23. 主要文献 -->
	<xsl:template match="ns:MainLiterature">
		<xsl:for-each select="ns:Reference">
			<p>
				<xsl:attribute name="class"><xsl:value-of select="'wordBreak'" /></xsl:attribute>
				<a>
					<xsl:attribute name="name"><xsl:value-of select="@id" /></xsl:attribute>
					<xsl:value-of select="concat(position(),') ')" />
					<xsl:apply-templates select="self::node()" mode="content-TYPE" />
				</a>
			</p>
		</xsl:for-each>
	</xsl:template>


	<!-- 24. 文献請求先及び問い合わせ先 -->
	<xsl:template match="ns:AddresseeInfo">
		<div style="margin-bottom:10px;">
			<p><xsl:apply-templates select="ns:AddresseeOfInquiry" mode="content-TYPE" /></p>
			<p><xsl:apply-templates select="ns:Address" mode="content-TYPE" /></p>
			<xsl:apply-templates select="ns:ContactInformation" mode="VariousForm-TYPE" />
		</div>
	</xsl:template>


	<!-- 25. 保険給付上の注意 -->
	<xsl:template match="ns:AttentionOfInsurance">
		<xsl:apply-templates select="ns:ContentOfAttentionOfInsurance" mode="VariousForm-TYPE">
			<xsl:with-param name="index" select="25" />
			<xsl:with-param name="level" select="1" />
		</xsl:apply-templates>
	</xsl:template>


	<!-- 26. 製造販売業者等 -->
	<xsl:template match="ns:Manufacturer">
		<xsl:param name="indx" select="''" />
		<div>
			<xsl:attribute name="class"><xsl:value-of select="'section'" /></xsl:attribute>
			<xsl:attribute name="data-level">
				<xsl:value-of select="'2'"/>
			</xsl:attribute>
			<xsl:apply-templates select="self::node()" mode="addModified" />
			<h3>
				<xsl:attribute name="class"><xsl:value-of select="'section_header'" /></xsl:attribute>
				26.<xsl:value-of select="concat($indx, ' ')" />
				<xsl:apply-templates select="ns:TypeOfIndustry" mode="content-TYPE" />
			</h3>
			<p style="margin-left:15px;"><xsl:apply-templates select="ns:Name" mode="content-TYPE" /></p>
			<p style="margin-left:15px;"><xsl:apply-templates select="ns:Address" mode="content-TYPE" /></p>
		</div>
	</xsl:template>


	<!-- 【データ型テンプレート】 -->

	<!-- 独自型 -->

	<!-- contentOrContentBaseWithXMLLANGoptional-O-TYPE -->
	<xsl:template match="ns:*" mode="contentOrContentBaseWithXMLLANGoptional-O-TYPE">
		<xsl:choose>
			<xsl:when test="count(ns:Lang)>0">
				<xsl:apply-templates select="self::node()" mode="content-TYPE" />
			</xsl:when>
			<xsl:otherwise>
				<xsl:apply-templates select="self::node()" mode="contentBaseWithXMLLANGoptional-TYPE" />
			</xsl:otherwise>
		</xsl:choose>
	</xsl:template>


	<!-- RepeatedContentBaseWithXMLLANGoptional-O-TYPE -->
	<xsl:template match="ns:*" mode="RepeatedContentBaseWithXMLLANGoptional-O-TYPE">
		<xsl:param name="element" select="ns:*" />
		<xsl:apply-templates select="self::node()" mode="RepeatedElement-BLK">
			<xsl:with-param name="content" select="'contentBaseWithXMLLANGoptional-TYPE'" />
			<xsl:with-param name="element" select="$element" />
		</xsl:apply-templates>
	</xsl:template>


	<xsl:template match="ns:*" mode="RepeatedDetails-TYPE">
		<xsl:param name="element" select="ns:*" />
		<xsl:param name="localname" select="''" />
		<xsl:apply-templates select="self::node()" mode="RepeatedElement-BLK">
			<xsl:with-param name="content" select="'content-TYPE'" />
			<xsl:with-param name="element" select="$element" />
			<xsl:with-param name="localname" select="$localname" />
		</xsl:apply-templates>
	</xsl:template>


	<!-- cdata.contentBaseWithXMLLANGoptional-TYPE -->
	<xsl:template match="ns:*" mode="contentBaseWithXMLLANGoptional-TYPE">
		<xsl:param name="modifiedflg" select="''" />
		<xsl:for-each select="node()">
			<xsl:choose>
				<xsl:when test="local-name(self::node())='Bold'">
					<strong>
						<xsl:apply-templates select="self::node()" mode="contentBaseWithXMLLANGoptional-TYPE" />
					</strong>
				</xsl:when>
				<xsl:when test="local-name(self::node())='Italic'">
					<em>
						<xsl:apply-templates select="self::node()" mode="contentBaseWithXMLLANGoptional-TYPE" />
					</em>
				</xsl:when>
				<xsl:when test="local-name(self::node())='Under'">
					<u>
						<xsl:apply-templates select="self::node()" mode="contentBaseWithXMLLANGoptional-TYPE" />
					</u>
				</xsl:when>
				<xsl:when test="local-name(self::node())='Sup'">
					<sup>
						<xsl:apply-templates select="self::node()" mode="contentBaseWithXMLLANGoptional-TYPE" />
					</sup>
				</xsl:when>
				<xsl:when test="local-name(self::node())='Sub'">
					<sub>
						<xsl:apply-templates select="self::node()" mode="contentBaseWithXMLLANGoptional-TYPE" />
					</sub>
				</xsl:when>
				<xsl:when test="local-name(self::node())='InlineGraphic'">
					<img width="1" height="1">
						<!-- H29添付文書XML化対応 START -->
						<xsl:attribute name="src">figures/<xsl:value-of select="@gfname" /></xsl:attribute>
						<!-- H29添付文書XML化対応 END -->
						<xsl:if test="@scale">
							<xsl:attribute name="data-scale"><xsl:value-of select="@scale" /></xsl:attribute>
						</xsl:if>
					</img>
				</xsl:when>
				<xsl:when test="local-name(self::node())='Modified'">
					<xsl:variable name="data-lastCount" select="count(//*[contains(@modified,'前回')])" />
					<xsl:choose>
						<xsl:when test="@ref='今回'">
							<xsl:choose>
								<xsl:when test="$data-lastCount>0">
									**<xsl:apply-templates select="self::node()" mode="contentBaseWithXMLLANGoptional-TYPE" />
								</xsl:when>
								<xsl:otherwise>
									*<xsl:apply-templates select="self::node()" mode="contentBaseWithXMLLANGoptional-TYPE" />
								</xsl:otherwise>
							</xsl:choose>
						</xsl:when>
						<xsl:when test="@ref='前回'">
							*<xsl:apply-templates select="self::node()" mode="contentBaseWithXMLLANGoptional-TYPE" />
						</xsl:when>
					</xsl:choose>
				</xsl:when>
				<xsl:when test="local-name(self::node())='ApprovalBrandNameRef'">
					<xsl:variable name="id" select="@ref" />
					<span class="ApprovalBrandNameRef">
						<xsl:apply-templates select="/ns:PackIns/ns:ApprovalEtc/ns:DetailBrandName[@id=$id]/ns:ApprovalBrandName" mode="content-TYPE" />
					</span>
				</xsl:when>
				<xsl:when test="local-name(self::node())='ReferenceBookRef'">
					<xsl:variable name="id" select="@ref" />
					<xsl:choose>
						<xsl:when test="count(/ns:PackIns/ns:MainLiterature/ns:Reference[@id=$id])!=0">
							<xsl:for-each select="/ns:PackIns/ns:MainLiterature/ns:Reference">
								<xsl:if test="$id=@id">
									<sup class="ReferenceBookRef">
										<a>
											<xsl:attribute name="href">#<xsl:value-of select="@id" /></xsl:attribute>
											<xsl:value-of select="position()" />)
										</a>
									</sup>
								</xsl:if>
							</xsl:for-each>
						</xsl:when>
						<xsl:otherwise>
							<sup>（文献参照切れ）</sup>
						</xsl:otherwise>
					</xsl:choose>
				</xsl:when>
				<xsl:when test="local-name(self::node())='EmbeddingText'">
					<xsl:variable name="id" select="@ref" />
					<xsl:apply-templates select="/ns:PackIns/ns:CompositionAndProperty//ns:*[@id=$id]" mode="contentOrContentBaseWithXMLLANGoptional-O-TYPE" />
				</xsl:when>
				<xsl:when test="local-name(self::node())='CommentRef' or local-name(self::node())='Comment'">
					<xsl:apply-templates select="self::node()" />
				</xsl:when>
				<xsl:when test="local-name(self::node())='HeaderRef'">
					<a class="HeaderRef">
						<xsl:attribute name="href">#<xsl:value-of select="@ref" /></xsl:attribute>
						<xsl:if test="count(self::node()[@remarks])!=0">
						<xsl:attribute name="data-remarks">
							<xsl:value-of select="@remarks" />
						</xsl:attribute>
						</xsl:if>
					</a>
				</xsl:when>
				<xsl:when test="local-name(self::node())='Link'">
					<a class="Link" target="_brank">
						<xsl:attribute name="href"><xsl:value-of select="@url" /></xsl:attribute>
						<xsl:apply-templates select="self::node()" mode="contentBaseWithXMLLANGoptional-TYPE" />
					</a>
				</xsl:when>
				<xsl:when test="local-name(self::node())='enter'">
					<br />
				</xsl:when>
				<xsl:otherwise>
					<!-- スペースを変換-->
					<xsl:call-template name="string-replace">
						<xsl:with-param name="text" select="self::node()" />
						<xsl:with-param name="replace" select="' '" />
						<xsl:with-param name="by" select="'&#160;'" />
					</xsl:call-template>
				</xsl:otherwise>
			</xsl:choose>
		</xsl:for-each>
	</xsl:template>

	<!-- 置換テンプレート -->
	<xsl:template name="string-replace">
		<xsl:param name="text" />
		<xsl:param name="replace" />
		<xsl:param name="by" />
		<xsl:choose>
			<xsl:when test="$text = '' or $replace = ''or not($replace)" >
				<xsl:value-of select="$text" />
			</xsl:when>
			<xsl:when test="contains($text, $replace)">
				<xsl:value-of select="substring-before($text,$replace)" />
				<xsl:value-of select="$by" />
				<xsl:call-template name="string-replace">
				<xsl:with-param name="text" select="substring-after($text,$replace)" />
					<xsl:with-param name="replace" select="$replace" />
					<xsl:with-param name="by" select="$by" />
				</xsl:call-template>
			</xsl:when>
			<xsl:otherwise>
				<xsl:value-of select="$text" />
			</xsl:otherwise>
		</xsl:choose>
	</xsl:template>

	<!-- 注釈参照テンプレート -->
	<xsl:template match="ns:CommentRef">
		<xsl:variable name="id" select="@ref" />
		<xsl:choose>
			<xsl:when test="count(//ns:Comment[@id=$id])!=0">
				<xsl:for-each select="//ns:Comment[count(ancestor::ns:Lang[@xml:lang=$lang])=1][count(ns:Lang[@xml:lang=$lang])=1]|
					//ns:Comment[count(ancestor::ns:Lang)=0][count(ns:Lang[@xml:lang=$lang])=1]">
					<xsl:if test="@id=$id">
						<sup class="CommentRef">
							<xsl:attribute name="data-id"><xsl:value-of select="$id" /></xsl:attribute>
							<a>
								<xsl:attribute name="href">#<xsl:value-of select="@id" /></xsl:attribute>
								注<span class="CommentRefNum"><xsl:value-of select="position()" /></span>)
							</a>
						</sup>
					</xsl:if>
				</xsl:for-each>
			</xsl:when>
			<xsl:otherwise>
				<sup>（注釈参照切れ）</sup>
			</xsl:otherwise>
		</xsl:choose>
	</xsl:template>

	<!-- 注釈コメントテンプレート -->
	<xsl:template match="ns:Comment">
		<xsl:variable name="thisId" select="self::node()/@id" />
		<div class="Comment" style="margin-left:15px">
			<xsl:attribute name="data-id"><xsl:value-of select="$thisId" /></xsl:attribute>
			<xsl:for-each select="//ns:Comment[count(ancestor::ns:Lang[@xml:lang=$lang])=1][count(ns:Lang[@xml:lang=$lang])=1]|
				//ns:Comment[count(ancestor::ns:Lang)=0][count(ns:Lang[@xml:lang=$lang])=1]">
				<xsl:if test="self::node()/@id=$thisId">
					<a>
						<xsl:attribute name="name"><xsl:value-of select="@id" /></xsl:attribute>
						注<span class="CommentNum"><xsl:value-of select="position()" /></span>)
					</a>
				</xsl:if>
			</xsl:for-each>
			<xsl:apply-templates select="self::node()" mode="content-TYPE" />
		</div>
	</xsl:template>

	<!-- cdata.content-TYPE型 -->
	<xsl:template match="ns:*" mode="content-TYPE">
		<xsl:variable name="data-lastCount" select="count(//*[contains(@modified,'前回')])" />
		<xsl:if test="@modified='前回'">
			<span contenteditable="false" class="revisionPrev-editor">*</span>
		</xsl:if>
		<xsl:if test="@modified='今回'">
			<xsl:choose>
				<xsl:when test="$data-lastCount>0">
					<span contenteditable="false" class="revisionThis-editor">**</span>
				</xsl:when>
				<xsl:otherwise>
					<span contenteditable="false" class="revisionThis-editor">*</span>
				</xsl:otherwise>
			</xsl:choose>
		</xsl:if>
		<xsl:if test="@modified='前回 今回'">
			<span contenteditable="false" class="revisionPrevThis-editor">**,*</span>
		</xsl:if>
		<xsl:if test="@modified='今回 前回'">
			<span contenteditable="false" class="revisionPrevThis-editor">**,*</span>
		</xsl:if>
		<xsl:apply-templates select="ns:Lang[@xml:lang=$lang]" mode="contentBaseWithXMLLANGoptional-TYPE" />
	</xsl:template>

	<!-- VariousForm-TYPE型 -->
	<xsl:template match="ns:*" mode="VariousForm-TYPE">
		<xsl:param name="index" select="''" />
		<xsl:param name="level" select="'99'" />
		<div class="VariousForm">
			<xsl:apply-templates select="(ns:Detail|ns:OrderedList|ns:UnorderedList|ns:SimpleList|ns:TblBlock|ns:Graphic)">
				<xsl:with-param name="index" select="$index" />
				<xsl:with-param name="level" select="$level" />
			</xsl:apply-templates>
		</div>
	</xsl:template>

	<!-- Detail要素 -->
	<xsl:template match="ns:Detail">
		<p><xsl:apply-templates select="self::node()" mode="content-TYPE" /></p>
	</xsl:template>

	<!-- OrderedList要素 -->
	<xsl:template match="ns:OrderedList">
		<xsl:param name="index" select="''" />
		<xsl:param name="level" select="'99'" />
		<ol>
			<xsl:apply-templates select="self::node()" mode="HeaderDetailList-TYPE">
				<xsl:with-param name="index" select="$index" />
				<xsl:with-param name="level" select="$level+1" />
			</xsl:apply-templates>
		</ol>
	</xsl:template>

	<!-- UnorderedList要素 -->
	<xsl:template match="ns:UnorderedList">
		<xsl:param name="index" select="''" />
		<xsl:param name="level" select="'99'" />
		<ul>
					<xsl:attribute name="style">list-style-type: <xsl:value-of select="@type" /></xsl:attribute>
			<xsl:apply-templates select="self::node()" mode="HeaderDetailList-TYPE">
				<xsl:with-param name="index" select="$index" />
				<xsl:with-param name="level" select="$level" />
			</xsl:apply-templates>
		</ul>
	</xsl:template>

	<!-- SimpleList要素 -->
	<xsl:template match="ns:SimpleList">
		<xsl:param name="index" select="''" />
		<xsl:param name="level" select="'99'" />
		<ul class="SimpleList">
			<xsl:apply-templates select="self::node()" mode="HeaderDetailList-TYPE">
				<xsl:with-param name="index" select="$index" />
				<xsl:with-param name="level" select="$level" />
			</xsl:apply-templates>
		</ul>
	</xsl:template>

	<!-- TblBlock要素 -->
	<xsl:template match="ns:TblBlock">
		<table border="1">
			<xsl:attribute name="style">
				width: <xsl:value-of select="ns:WidthDefinition/@totalWidth" />
			</xsl:attribute>
			<xsl:attribute name="class">TblBlock_table</xsl:attribute>
			<xsl:apply-templates select="ns:TblCaption" />
			<xsl:apply-templates select="ns:SimpTblHead" />
			<xsl:apply-templates select="ns:SimpleTable" />
		</table>
	</xsl:template>

	<!-- TblCaption要素 -->
	<xsl:template match="ns:TblCaption">
		<caption>
			<xsl:if test="count(@align)!=0">
				<xsl:attribute name="align"><xsl:value-of select="@align"/></xsl:attribute>
			</xsl:if>
			<xsl:apply-templates select="self::node()" mode="content-TYPE" />
		</caption>
	</xsl:template>

	<!-- SimpTblHead要素 -->
	<xsl:template match="ns:SimpTblHead">
		<xsl:if test="count(ns:Detail)!=0">
			<tr>
				<xsl:for-each select="ns:Detail">
					<xsl:variable name="position" select="position()" />
					<th>
						<xsl:attribute name="style">
							width:<xsl:value-of select="../../ns:WidthDefinition/ns:Col[position()=$position]/@width" />
						</xsl:attribute>
						<xsl:attribute name="rowspan">
							<xsl:value-of select="@rspan" />
						</xsl:attribute>
						<xsl:attribute name="colspan">
							<xsl:value-of select="@cspan" />
						</xsl:attribute>
						<xsl:apply-templates select="self::node()" mode="content-TYPE" />
					</th>
				</xsl:for-each>
			</tr>
		</xsl:if>
	</xsl:template>

	<!-- SimpleTable要素 -->
	<xsl:template match="ns:SimpleTable">
		<xsl:for-each select="ns:SimpTblRow">
			<xsl:variable name="rowPosition" select="position()" />
			<tr>
				<xsl:for-each select="ns:SimpTblCell">
					<xsl:variable name="cellPosition" select="position()" />
					<td>
						<xsl:attribute name="style">
							<xsl:if test="count(@align)!=0">
								text-align:<xsl:value-of select="@align" />;
							</xsl:if>
							<xsl:if test="count(@valign)!=0">
								vertical-align:<xsl:value-of select="@valign" />;
							</xsl:if>
						</xsl:attribute>
						<xsl:attribute name="rowspan">
							<xsl:value-of select="@rspan" />
						</xsl:attribute>
						<xsl:attribute name="colspan">
							<xsl:value-of select="@cspan" />
						</xsl:attribute>
						<xsl:apply-templates select="self::node()" mode="VariousForm-TYPE" >
							<xsl:with-param name="index" select="'1'" />
							<xsl:with-param name="level" select="'3'" />
						</xsl:apply-templates>
					</td>
				</xsl:for-each>
			</tr>
		</xsl:for-each>
		<!-- SimpTblFoot要素 -->
		<xsl:if test="count(../ns:SimpTblFoot/ns:Detail)>0">
			<tr class="tableFooter">
				<th>
					<xsl:if test="count(../ns:SimpTblFoot/@align)!=0">
						<xsl:attribute name="style">
							text-align:<xsl:value-of select="../ns:SimpTblFoot/@align"/>;
						</xsl:attribute>
					</xsl:if>
					<xsl:if test="count(../ns:WidthDefinition/ns:Col)!=0">
						<xsl:attribute name="colspan">
							<xsl:value-of select="count(../ns:WidthDefinition/ns:Col)" />
						</xsl:attribute>
					</xsl:if>
					<xsl:for-each select="../ns:SimpTblFoot/ns:Detail">
						<xsl:if test="count(ns:Lang[@xml:lang=$lang])!=0">
							<p>
								<xsl:apply-templates select="self::node()" mode="content-TYPE" />
							</p>
						</xsl:if>
					</xsl:for-each>
				</th>
			</tr>
		</xsl:if>
		<!-- Col要素 -->
		<xsl:if test="count(../ns:WidthDefinition/ns:Col)!=0">
			<tr>
				<xsl:for-each select="../ns:WidthDefinition/ns:Col">
					<td>
						<xsl:attribute name="colWidth">
							<xsl:value-of select="self::node()/@width"/>
						</xsl:attribute>
					</td>
				</xsl:for-each>
			</tr>
		</xsl:if>
	</xsl:template>

	<!-- Graphic要素 -->
	<xsl:template match="ns:Graphic">
		<figure>
			<xsl:for-each select="node()">
				<xsl:choose>
					<xsl:when test="local-name()='GraphicCaption'">
						<figcaption><xsl:apply-templates select="self::node()" mode="content-TYPE" /></figcaption>
					</xsl:when>
					<xsl:when test="local-name()='GraphicBody'">
						<img width="1" height="1">
							<!-- H29添付文書XML化対応 START -->
							<xsl:attribute name="src">figures/<xsl:value-of select="@gfname" /></xsl:attribute>
							<!-- H29添付文書XML化対応 END -->
							<xsl:if test="@scale">
								<xsl:attribute name="data-scale"><xsl:value-of select="@scale" /></xsl:attribute>
							</xsl:if>
						</img>
					</xsl:when>
				</xsl:choose>
			</xsl:for-each>
		</figure>
	</xsl:template>

	<!-- HeaderDetailList-TYPE型 -->
	<xsl:template match="ns:*" mode="HeaderDetailList-TYPE">
		<xsl:param name="index" select="''" />
		<xsl:param name="level" select="'99'" />
		<xsl:param name="localname" select="''" />
		<xsl:for-each select="ns:Item">
			<a>
				<xsl:attribute name="name"><xsl:value-of select="@id" /></xsl:attribute>
			</a>
			<li>
				<xsl:attribute name="id"><xsl:value-of select="@id" /></xsl:attribute>

				<xsl:if test="local-name(parent::node())='OrderedList' and $index!='' and $level &lt; 4">
					<!-- セクションレベル属性 -->
					<xsl:attribute name="data-level">
						<xsl:value-of select="$level" />
					</xsl:attribute>
					<xsl:apply-templates select="self::node()" mode="addModified" />
				</xsl:if>

				<xsl:variable name="localIndex">
					<xsl:variable name="itemNum">
					<xsl:choose>
						<xsl:when test="parent::ns:OrderedList/@numberContinued='true' and local-name(parent::ns:OrderedList/parent::ns:Item/parent::node())!='OrderedList'">
							<xsl:value-of select="count(parent::ns:OrderedList/parent::ns:Item/preceding-sibling::ns:Item/ns:OrderedList/ns:Item)+
							count(parent::ns:OrderedList/preceding-sibling::ns:OrderedList/ns:Item)+position()" />
						</xsl:when>
						<xsl:when test="parent::ns:OrderedList/@numberContinued='true'">
							<xsl:value-of select="count(parent::ns:OrderedList/preceding-sibling::ns:OrderedList/ns:Item)+position()" />
						</xsl:when>
						<xsl:when test="local-name(parent::node())='OrderedList'">
							<xsl:value-of select="position()" />
						</xsl:when>
					</xsl:choose>
					</xsl:variable>
					<!-- 項番を作成 -->
					<xsl:choose>
						<xsl:when test="$index!='' and $level &lt; 4">
							<xsl:value-of select="concat($index, '.', $itemNum)" />
						</xsl:when>
						<xsl:when test="$index!='' and $level = 4">
							<xsl:value-of select="concat('(', $itemNum, ')')" />
						</xsl:when>
						<xsl:otherwise>
							<xsl:value-of select="' '" />
						</xsl:otherwise>
					</xsl:choose>
				</xsl:variable>
				<xsl:if test="local-name(parent::node())='OrderedList'">
					<span class="section_header">
						<xsl:value-of select="concat($localIndex,' ')" />
					</span>
				</xsl:if>
				<xsl:for-each select="ns:Header|ns:Detail|ns:OrderedList|ns:UnorderedList|ns:SimpleList|ns:TblBlock|ns:Graphic">
					<xsl:choose>
						<xsl:when test="local-name()='OrderedList' or local-name()='SimpleList' or local-name()='UnorderedList'">
							<xsl:choose>
								<xsl:when test="local-name(parent::ns:Item/parent::node())='OrderedList' and $index!='' and $level &lt; 4">
									<xsl:apply-templates select="self::node()">
										<xsl:with-param name="index" select="$localIndex" />
										<xsl:with-param name="level" select="$level" />
									</xsl:apply-templates>
								</xsl:when>
								<xsl:otherwise>
									<xsl:apply-templates select="self::node()">
										<xsl:with-param name="index" select="$index" />
										<xsl:with-param name="level" select="$level" />
									</xsl:apply-templates>
								</xsl:otherwise>
							</xsl:choose>
						</xsl:when>
						<xsl:when test="local-name()='Detail' and position()=1 and count(parent::node()/ns:Header)=0">
							<xsl:apply-templates select="self::node()" mode="content-TYPE" />
						</xsl:when>
						<xsl:otherwise>
							<xsl:apply-templates select="self::node()" />
						</xsl:otherwise>
					</xsl:choose>
				</xsl:for-each>
			</li>
		</xsl:for-each>
	</xsl:template>

	<!-- Header要素 -->
	<xsl:template match="ns:Header">
		<span class="Header-preview"><xsl:apply-templates select="self::node()" mode="content-TYPE" /></span>
	</xsl:template>

	<!-- Repeated-Details-TYPE型 -->
	<xsl:template match="ns:*" mode="Repeated-Details-TYPE">
		<xsl:for-each select="ns:Detail">
			<p><xsl:apply-templates select="self::node()" mode="content-TYPE" /></p>
		</xsl:for-each>
	</xsl:template>

	<!-- TblBlocks-TYPE型 -->
	<xsl:template match="ns:*" mode="TblBlocks-TYPE">
		<xsl:apply-templates select="ns:TblBlock" />
	</xsl:template>


	<!-- 見出し参照用テンプレート -->

	<!-- 3. 組成・性状 -->
	<xsl:template match="ns:CompositionAndProperty" mode="ForHeaderRef">
		<xsl:apply-templates select="self::node()" mode="Single-ForHeaderRef">
			<xsl:with-param name="index" select="3" />
		</xsl:apply-templates>
		<xsl:if test="$drugType='Vaccine' or $drugType='Antitoxin'">
			<xsl:apply-templates select="ns:OverviewOfRecipe" mode="Single-ForHeaderRef">
				<xsl:with-param name="index" select="3.1" />
			</xsl:apply-templates>
		</xsl:if>
		<xsl:apply-templates select="ns:Composition" mode="Single-ForHeaderRef">
			<xsl:with-param name="index">
				<xsl:choose>
					<xsl:when test="$drugType='Vaccine' or $drugType='Antitoxin'">
						<xsl:value-of select="'3.2'" />
					</xsl:when>
					<xsl:otherwise>
						<xsl:value-of select="'3.1'" />
					</xsl:otherwise>
				</xsl:choose>
			</xsl:with-param>
		</xsl:apply-templates>
		<xsl:apply-templates select="ns:Property" mode="Single-ForHeaderRef">
			<xsl:with-param name="index">
				<xsl:choose>
					<xsl:when test="$drugType='Vaccine' or $drugType='Antitoxin'">
						<xsl:value-of select="'3.3'" />
					</xsl:when>
					<xsl:otherwise>
						<xsl:value-of select="'3.2'" />
					</xsl:otherwise>
				</xsl:choose>
			</xsl:with-param>
		</xsl:apply-templates>
	</xsl:template>

	<!-- 6. 用法及び用量 -->
	<xsl:template match="ns:InfoDoseAdmin" mode="ForHeaderRef">
		<xsl:apply-templates select="self::node()" mode="Single-ForHeaderRef">
			<xsl:with-param name="index" select="6" />
		</xsl:apply-templates>
		<xsl:apply-templates select="ns:DoseAdmin" mode="VariousForm-ForHeaderRef">
			<xsl:with-param name="index" select="6" />
			<xsl:with-param name="level" select="1" />
		</xsl:apply-templates>
	</xsl:template>

	<!-- 9. 特定の背景を有する患者に関する注意 -->
	<xsl:template match="ns:UseInSpecificPopulations" mode="ForHeaderRef">
		<xsl:apply-templates select="self::node()" mode="Single-ForHeaderRef">
			<xsl:with-param name="index" select="9" />
		</xsl:apply-templates>
		<xsl:apply-templates select="ns:UseInPatientsWithComplicationsOrHistoryOfDiseasesEtc" mode="VariousForm-ForHeaderRef">
			<xsl:with-param name="index" select="9.1" />
			<xsl:with-param name="level" select="2" />
		</xsl:apply-templates>
		<xsl:apply-templates select="ns:PatientsWithRenalImpairment" mode="VariousForm-ForHeaderRef">
			<xsl:with-param name="index" select="9.2" />
			<xsl:with-param name="level" select="2" />
		</xsl:apply-templates>
		<xsl:apply-templates select="ns:PatientsWithHepaticImpairment" mode="VariousForm-ForHeaderRef">
			<xsl:with-param name="index" select="9.3" />
			<xsl:with-param name="level" select="2" />
		</xsl:apply-templates>
		<xsl:apply-templates select="ns:MalesAndFemalesOfReproductivePotential" mode="VariousForm-ForHeaderRef">
			<xsl:with-param name="index" select="9.4" />
			<xsl:with-param name="level" select="2" />
		</xsl:apply-templates>
		<xsl:apply-templates select="ns:UseInPregnant" mode="VariousForm-ForHeaderRef">
			<xsl:with-param name="index" select="9.5" />
			<xsl:with-param name="level" select="2" />
		</xsl:apply-templates>
		<xsl:apply-templates select="ns:UseInNursing" mode="VariousForm-ForHeaderRef">
			<xsl:with-param name="index" select="9.6" />
			<xsl:with-param name="level" select="2" />
		</xsl:apply-templates>
		<xsl:apply-templates select="ns:PediatricUse" mode="VariousForm-ForHeaderRef">
			<xsl:with-param name="index" select="9.7" />
			<xsl:with-param name="level" select="2" />
		</xsl:apply-templates>
		<xsl:apply-templates select="ns:UseInTheElderly" mode="VariousForm-ForHeaderRef">
			<xsl:with-param name="index" select="9.8" />
			<xsl:with-param name="level" select="2" />
		</xsl:apply-templates>
	</xsl:template>

	<!-- 10. 相互作用 -->
	<xsl:template match="ns:Interactions" mode="ForHeaderRef">
		<xsl:apply-templates select="self::node()" mode="Single-ForHeaderRef">
			<xsl:with-param name="index" select="10" />
		</xsl:apply-templates>
		<xsl:apply-templates select="ns:ContraIndicatedCombinations" mode="Single-ForHeaderRef">
			<xsl:with-param name="index" select="10.1" />
		</xsl:apply-templates>
		<xsl:apply-templates select="ns:PrecautionsForCombinations" mode="Single-ForHeaderRef">
			<xsl:with-param name="index" select="10.2" />
		</xsl:apply-templates>
	</xsl:template>

	<!-- 11. 副作用 -->
	<xsl:template match="ns:AdverseEvents" mode="ForHeaderRef">
		<xsl:apply-templates select="self::node()" mode="Single-ForHeaderRef">
			<xsl:with-param name="index" select="11" />
		</xsl:apply-templates>
		<xsl:apply-templates select="ns:SeriousAdverseEvents" mode="Single-ForHeaderRef">
			<xsl:with-param name="index" select="11.1" />
		</xsl:apply-templates>
		<xsl:apply-templates select="ns:SeriousAdverseEvents/ns:SeriousAdverse" mode="VariousForm-ForHeaderRef">
			<xsl:with-param name="index" select="11.1" />
			<xsl:with-param name="level" select="2" />
		</xsl:apply-templates>
		<xsl:apply-templates select="ns:OtherAdverseEvents" mode="Single-ForHeaderRef">
			<xsl:with-param name="index" select="11.2" />
		</xsl:apply-templates>
	</xsl:template>

	<!-- 14. 適用上の注意 -->
	<xsl:template match="ns:PrecautionsForApplication" mode="ForHeaderRef">
		<xsl:apply-templates select="self::node()" mode="Single-ForHeaderRef">
			<xsl:with-param name="index" select="14" />
		</xsl:apply-templates>
		<xsl:apply-templates select="self::node()" mode="OtherInformation-ForHeaderRef">
			<xsl:with-param name="index" select="14" />
		</xsl:apply-templates>
	</xsl:template>

	<!-- 15. その他の注意 -->
	<xsl:template match="ns:OtherPrecautions" mode="ForHeaderRef">
		<xsl:apply-templates select="self::node()" mode="Single-ForHeaderRef">
			<xsl:with-param name="index" select="15" />
		</xsl:apply-templates>
		<xsl:apply-templates select="ns:InformationBasedOnClinicalUse" mode="VariousForm-ForHeaderRef">
			<xsl:with-param name="index" select="15.1" />
			<xsl:with-param name="level" select="2" />
		</xsl:apply-templates>
		<xsl:apply-templates select="ns:InformationBasedOnNonclinicalStudies" mode="VariousForm-ForHeaderRef">
			<xsl:with-param name="index" select="15.2" />
			<xsl:with-param name="level" select="2" />
		</xsl:apply-templates>
		<xsl:apply-templates select="self::node()" mode="OtherInformation-ForHeaderRef">
			<xsl:with-param name="index" select="15" />
			<xsl:with-param name="startIndex" select="3" />
		</xsl:apply-templates>
	</xsl:template>

	<!-- 16. 薬物動態 -->
	<xsl:template match="ns:Pharmacokinetics" mode="ForHeaderRef">
		<xsl:apply-templates select="self::node()" mode="Single-ForHeaderRef">
			<xsl:with-param name="index" select="16" />
		</xsl:apply-templates>
		<xsl:apply-templates select="ns:BloodLevel" mode="VariousForm-ForHeaderRef">
			<xsl:with-param name="index" select="16.1" />
			<xsl:with-param name="level" select="2" />
		</xsl:apply-templates>
		<xsl:apply-templates select="ns:Absorption" mode="VariousForm-ForHeaderRef">
			<xsl:with-param name="index" select="16.2" />
			<xsl:with-param name="level" select="2" />
		</xsl:apply-templates>
		<xsl:apply-templates select="ns:Distribution" mode="VariousForm-ForHeaderRef">
			<xsl:with-param name="index" select="16.3" />
			<xsl:with-param name="level" select="2" />
		</xsl:apply-templates>
		<xsl:apply-templates select="ns:Metabolism" mode="VariousForm-ForHeaderRef">
			<xsl:with-param name="index" select="16.4" />
			<xsl:with-param name="level" select="2" />
		</xsl:apply-templates>
		<xsl:apply-templates select="ns:Excretion" mode="VariousForm-ForHeaderRef">
			<xsl:with-param name="index" select="16.5" />
			<xsl:with-param name="level" select="2" />
		</xsl:apply-templates>
		<xsl:apply-templates select="ns:SpecificPopulation" mode="VariousForm-ForHeaderRef">
			<xsl:with-param name="index" select="16.6" />
			<xsl:with-param name="level" select="2" />
		</xsl:apply-templates>
		<xsl:apply-templates select="ns:DrugAndDrugInteractions" mode="VariousForm-ForHeaderRef">
			<xsl:with-param name="index" select="16.7" />
			<xsl:with-param name="level" select="2" />
		</xsl:apply-templates>
		<xsl:apply-templates select="ns:PharmacokineticsEtc" mode="VariousForm-ForHeaderRef">
			<xsl:with-param name="index" select="16.8" />
			<xsl:with-param name="level" select="2" />
		</xsl:apply-templates>
	</xsl:template>

	<!-- 17. 臨床成績 -->
	<xsl:template match="ns:ResultsOfClinicalTrials" mode="ForHeaderRef">
		<xsl:apply-templates select="self::node()" mode="Single-ForHeaderRef">
			<xsl:with-param name="index" select="17" />
		</xsl:apply-templates>
		<xsl:apply-templates select="ns:EfficacyAndSafety" mode="VariousForm-ForHeaderRef">
			<xsl:with-param name="index" select="17.1" />
			<xsl:with-param name="level" select="2" />
		</xsl:apply-templates>
		<xsl:apply-templates select="ns:PostMarketingSurveylancesEtc" mode="VariousForm-ForHeaderRef">
			<xsl:with-param name="index" select="17.2" />
			<xsl:with-param name="level" select="2" />
		</xsl:apply-templates>
		<xsl:apply-templates select="ns:ResultsOfClinicalTrialsEtc" mode="VariousForm-ForHeaderRef">
			<xsl:with-param name="index" select="17.3" />
			<xsl:with-param name="level" select="2" />
		</xsl:apply-templates>
	</xsl:template>

	<!-- 18. 薬効薬理 -->
	<xsl:template match="ns:EfficacyPharmacology" mode="ForHeaderRef">
		<xsl:apply-templates select="self::node()" mode="Single-ForHeaderRef">
			<xsl:with-param name="index" select="18" />
		</xsl:apply-templates>
		<xsl:apply-templates select="ns:MechanismOfAction" mode="VariousForm-ForHeaderRef">
			<xsl:with-param name="index" select="18.1" />
			<xsl:with-param name="level" select="2" />
		</xsl:apply-templates>
		<xsl:apply-templates select="ns:MeasurementMethod" mode="VariousForm-ForHeaderRef">
			<xsl:with-param name="index" select="18.1" />
			<xsl:with-param name="level" select="2" />
		</xsl:apply-templates>
		<xsl:apply-templates select="self::node()" mode="OtherInformation-ForHeaderRef">
			<xsl:with-param name="index" select="18" />
			<xsl:with-param name="startIndex" select="2" />
		</xsl:apply-templates>
	</xsl:template>

	<!-- 25. 保険給付上の注意 -->
	<xsl:template match="ns:AttentionOfInsurance" mode="ForHeaderRef">
		<xsl:apply-templates select="self::node()" mode="Single-ForHeaderRef">
			<xsl:with-param name="index" select="25" />
		</xsl:apply-templates>
		<xsl:apply-templates select="ns:ContentOfAttentionOfInsurance" mode="VariousForm-ForHeaderRef">
			<xsl:with-param name="index" select="25" />
			<xsl:with-param name="level" select="1" />
		</xsl:apply-templates>
	</xsl:template>

	<!-- OtherInformation -->
	<xsl:template match="ns:*" mode="OtherInformation-ForHeaderRef">
		<xsl:param name="index" select="''" />
		<xsl:param name="startIndex" select="1" />
		<xsl:for-each select="ns:OtherInformation">
			<xsl:variable name="nowIndex" select="concat($index, '.', $startIndex+position()-1)" />
			<xsl:apply-templates select="self::node()" mode="VariousForm-ForHeaderRef">
				<xsl:with-param name="index" select="$nowIndex" />
				<xsl:with-param name="level" select="2" />
			</xsl:apply-templates>
		</xsl:for-each>
	</xsl:template>

	<!-- VariousForm-TYPE型 -->
	<xsl:template match="ns:*" mode="VariousForm-ForHeaderRef">
		<xsl:param name="index" select="''" />
		<xsl:param name="level" select="'99'" />

		<xsl:apply-templates select="self::node()" mode="Single-ForHeaderRef">
			<xsl:with-param name="index" select="$index" />
		</xsl:apply-templates>

		<xsl:for-each select="ns:OrderedList|ns:UnorderedList|ns:SimpleList">
			<xsl:choose>
				<xsl:when test="local-name()='OrderedList'">
					<xsl:apply-templates select="self::node()" mode="HeaderDetailList-ForHeaderRef">
						<xsl:with-param name="index" select="$index" />
						<xsl:with-param name="level" select="$level+1" />
					</xsl:apply-templates>
				</xsl:when>
				<xsl:otherwise>
					<xsl:apply-templates select="self::node()" mode="HeaderDetailList-ForHeaderRef">
						<xsl:with-param name="index" select="$index" />
						<xsl:with-param name="level" select="$level" />
					</xsl:apply-templates>
				</xsl:otherwise>
			</xsl:choose>
		</xsl:for-each>
	</xsl:template>

	<!-- HeaderDetailList-TYPE型 -->
	<xsl:template match="ns:*" mode="HeaderDetailList-ForHeaderRef">
		<xsl:param name="index" select="''" />
		<xsl:param name="level" select="'99'" />
		<xsl:for-each select="ns:Item">
			<xsl:variable name="localIndex">
				<xsl:choose>
					<xsl:when test="parent::ns:OrderedList/@numberContinued='true' and local-name(parent::ns:OrderedList/parent::ns:Item/parent::node())!='OrderedList'">
						<xsl:variable name="itemNum" select="count(parent::ns:OrderedList/parent::ns:Item/preceding-sibling::ns:Item/ns:OrderedList/ns:Item)+
							count(parent::ns:OrderedList/preceding-sibling::ns:OrderedList/ns:Item)+position()" />
						<xsl:value-of select="concat($index, '.', $itemNum)" />
					</xsl:when>
					<xsl:when test="parent::ns:OrderedList/@numberContinued='true'">
						<xsl:variable name="itemNum" select="count(parent::ns:OrderedList/preceding-sibling::ns:OrderedList/ns:Item)+position()" />
						<xsl:value-of select="concat($index, '.', $itemNum)" />
					</xsl:when>
					<xsl:when test="parent::ns:OrderedList">
						<xsl:value-of select="concat($index, '.', position())" />
					</xsl:when>
					<xsl:otherwise><xsl:value-of select="$index" /></xsl:otherwise>
				</xsl:choose>
			</xsl:variable>
			<!-- 見出し番号の作成 -->
			<xsl:if test="local-name(parent::node())='OrderedList' and $index!='' and $level &lt; 4 and @id!=''">
				<div>
					<xsl:attribute name="data-header-id"><xsl:value-of select="@id" /></xsl:attribute>
					<xsl:value-of select="$localIndex" />
				</div>
			</xsl:if>
			<xsl:for-each select="ns:OrderedList|ns:UnorderedList|ns:SimpleList">
				<xsl:choose>
					<xsl:when test="local-name(self::node())='OrderedList' and $index!='' and $level &lt; 4">
						<xsl:apply-templates select="self::node()" mode="HeaderDetailList-ForHeaderRef">
							<xsl:with-param name="index" select="$localIndex" />
							<xsl:with-param name="level" select="$level+1" />
						</xsl:apply-templates>
					</xsl:when>
					<xsl:when test="$index!='' and $level &lt; 4">
						<xsl:apply-templates select="self::node()" mode="HeaderDetailList-ForHeaderRef">
							<xsl:with-param name="index" select="$index" />
							<xsl:with-param name="level" select="$level" />
						</xsl:apply-templates>
					</xsl:when>
				</xsl:choose>
			</xsl:for-each>
		</xsl:for-each>
	</xsl:template>

	<!-- 見出し要素 -->
	<xsl:template match="ns:*" mode="Single-ForHeaderRef">
		<xsl:param name="index" select="''" />
		<xsl:param name="title" select="''" />
		<xsl:variable name="localname" select="local-name(self::node())" />
		<xsl:if test="@id!=''">
			<div>
				<xsl:attribute name="data-header-id"><xsl:value-of select="@id" /></xsl:attribute>
				<!-- 項番 -->
				<xsl:if test="$index!=''">
					<xsl:choose>
						<xsl:when test="contains($index, '.')">
							<xsl:value-of select="$index" />
						</xsl:when>
						<xsl:otherwise>
							<xsl:value-of select="concat($index, '.')" />
						</xsl:otherwise>
					</xsl:choose>
				</xsl:if>
				<xsl:if test="$title!=''">
					<xsl:value-of select="concat($title, '')" />
				</xsl:if>
			</div>
		</xsl:if>
	</xsl:template>

</xsl:stylesheet>
