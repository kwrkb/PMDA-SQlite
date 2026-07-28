$(function() {
	// 最下層の項目のレベル
	var maxLevel = 0;
	
	// 項目の改訂情報の数を求める
	$.each($('[data-level]'), function() {
		var level = parseInt($(this).attr('data-level'));
		var thisCount = $(this).attr('data-thisCount');
		var lastCount = $(this).attr('data-lastCount');
		
		var $childrenSection = $(this).find('[data-level="' + (level+1) + '"]');
		$.each($childrenSection, function() {
			thisCount = thisCount - $(this).attr('data-thisCount');
			lastCount = lastCount - $(this).attr('data-lastCount');
		});
		
		$(this).attr('data-thisCount', thisCount);
		$(this).attr('data-lastCount', lastCount);
		
		if (level > maxLevel && level != 99) {
			maxLevel = level;
		}
	});
	
	// 下の階層から改訂情報を判定する
	for (i=maxLevel-1; i>=1; i--) {
		$.each($('[data-level="' + i + '"]'), function() {
			var level = i;
			
			// 番号なしリスト、単純リストの場合は改訂記号の繰り上げ処理をスキップする
			if ($(this).get(0).tagName === 'LI') {
				if ($(this).get(0).parentNode.tagName === 'UL') {
					return true;
				}
			}

			// 子項目の改訂記号をカウント
			var $childrenSection = $(this).find('[data-level="' + (level+1) + '"]');
			var childrenCount = $childrenSection.length;
			var childrenThisCount = 0;
			var childrenLastCount = 0;
			$.each($childrenSection, function() {
				if ($(this).attr('data-thisCount') > 0) {
					childrenThisCount++;
				}
				if ($(this).attr('data-lastCount') > 0) {
					childrenLastCount++;
				}
			});
			
			// 全てに今回改訂が付与されていた場合
			if (childrenCount!=0 && childrenThisCount==childrenCount) {
				$(this).attr('data-thisCount', 1);
				$childrenSection.attr('data-thisCount', 0);
			}
			// 全てに前回改訂が付与されていた場合
			if (childrenCount!=0 && childrenLastCount==childrenCount) {
				$(this).attr('data-lastCount', 1);
				$childrenSection.attr('data-lastCount', 0);
			}
		});
	}

	// ドキュメント内の前回改訂があるか false:なし、true：あり
	var lastRevisionFlg = false;
	// htmlロード時に全体に前回改訂があるか判定する
	$('div').each(function () {
		var count = $(this).attr('data-lastCount');
		if (!isNaN(count)) {
			if (count > 0) {
				lastRevisionFlg = true;
				return;
			}
		}
	});
	
	// リストの場合も考慮
	if (!lastRevisionFlg) {
		$('li').each(function () {
			var count = $(this).attr('data-lastCount');
			if (!isNaN(count)) {
				if (count > 0) {
					lastRevisionFlg = true;
					return;
				}
			}
		});
	}

	// 改訂記号の付与
	$.each($('[data-level]'), function() {
		var thisCount = $(this).attr('data-thisCount');
		var lastCount = $(this).attr('data-lastCount');

		if (thisCount>0 && lastCount>0) {
			$(this).children('.section_header').prepend('<span style="margin-left:-30px;position:absolute;">**,*</span>');
		} else if (thisCount>0) {
			// ドキュメント中に前回改訂が存在する
			if (lastRevisionFlg) {
				$(this).children('.section_header').prepend('<span style="margin-left:-18px;position:absolute;">**</span>');
			} else {
				$(this).children('.section_header').prepend('<span style="margin-left:-18px;position:absolute;">*</span>');
			}
		} else if (lastCount>0) {
			$(this).children('.section_header').prepend('<span style="margin-left:-12px;position:absolute;">*</span>');
		}
	});

	// ヘッダ項目
	var headerName = ['DrugType', 'PackageInsertNo', 'CompanyIdentifier', 'DateOfPreparationOrRevision', 'Sccj', 'TherapeuticClassification', 'ApprovalEtc', 'GenericName', 'SupplementaryInformaitonOfVaccineStrain'];

	// ヘッダ項目の中の注釈を数える
	var headerCommentCnt = 0;
	var headerFirstId = '';

	// 注釈番号の採番しなおし
	$.each($('.contents').children('div'), function(i, child) {
		var childid = $(child).attr("id")!=undefined ? $(child).attr("id").replace('HDR_', '') : $(child).children('div').attr("id").replace('HDR_', '');
		$.each($(child).find('.CommentNum'), function(j, comment) {
			// ヘッダ項目は全体で連番
			if(headerName.indexOf(childid) != -1){
				headerCommentCnt++;
				$(comment).text(headerCommentCnt);
				headerFirstId = headerCommentCnt==1 ? childid : headerFirstId;
			// ヘッダ項目以外は大項目ごとに連番
			} else {
				// 1個しかない場合は、「注)」のみ
				if($(child).find('.CommentNum').length == 1){
					$(comment).text('');
				} else {
					$(comment).text(j + 1);
				}
			}
		});
	});

	// ヘッダ項目内の注釈が1つの場合、「注)」のみの表記にする
	if(headerCommentCnt == 1){
		$('#HDR_' + headerFirstId).find('.CommentNum').text('');
	}
	
	// 参照注釈番号の設定しなおし
	$.each($('.CommentRef'), function() {
		var $comment = $('.container .Comment[data-id="' + $(this).attr('data-id') + '"]');
		if($comment != undefined){
			//$(this).find('.CommentRefNum').text($comment.find('.CommentNum').text());
			if ($comment.length == 1) {
			    $(this).find('.CommentRefNum').text($comment.find('.CommentNum').text());
			} else {
			    var num = $(this).parent().next().find('.CommentNum').text();
			    $(this).find('.CommentRefNum').text(num);
			}
        }
	});
	
	// 見出し参照のテキスト挿入
	$.each($('.HeaderRef'), function () {
		var id = $(this).attr('href').replace('#', '');
		var className = $(this).attr('class');
		var text = $('#Header-data').find('[data-header-id="' + id + '"]').text();
		if (text != null && text != "") {
			text = '［' + text + ' 参照］';
			$(this).text(text);
		} else if ($(this).attr('data-remarks') != null) { // 見出し参照切れ（remarks属性あり）
			var encodeHtmlEntity = function (str) {
				return $('<div>').text(str).html().replace(/'/g, '&#39;').replace(/"/g, '&quot;');
			};
			var remarks = encodeHtmlEntity($(this).attr('data-remarks'));
			$(this).replaceWith('<span class="' + className + '" data-header-id="' + id + '" title = "' + remarks + '">（見出し参照切れ）</span>');
		} else { // 見出し参照切れ（remarks属性なし）
			$(this).replaceWith('<span class="' + className + '" data-header-id="' + id + '">（見出し参照切れ）</span>');
		}
	});

	$.each($('img'), function() {
		var $img = $(this);
		var scale = $img.data('scale') || 100;
		$img
			.css('width', $img[0].naturalWidth * scale / 100)
			.css('height', $img[0].naturalHeight * scale / 100);
	});

    // 表の列幅指定を適用する
	setTableColWidth();

	// 製品ごとに組成のテーブルのヘッダー結合
	var $headerCells = $('div#HDR_Composition table tr:eq(0) th:gt(0)');
	var $categoryCells = $('div#HDR_Composition table tr:eq(1) td:gt(0)');

	for (var index = 0; index < $headerCells.length; index++) {
		var $currentHeader = $headerCells.eq(index);

		// 製品の列数をカウント、同じ製品のセルを結合する
		var headerCspan = 1;
		if ($currentHeader.html() !== '') {
			$.each($currentHeader.nextAll('th'), function() {
				if ($currentHeader.html() === $(this).html()) {
					$(this).remove();
					headerCspan++;
				}
			});
		}
		$currentHeader.attr('colspan', headerCspan);
		
		// 製品の同列の構成のうち空の値を持つ列数をカウント
		var categoryCspan = 0;
		for (var categoryIndex = index; categoryIndex < index + headerCspan; categoryIndex++) {
			var categoryHtml = $categoryCells.eq(categoryIndex).html();
			if (categoryHtml === '' || categoryHtml === '\x0a') {
				categoryCspan++;
			}
		}
		
		// 製品の列数と空の構成の列数が一致する場合はセルを結合する
		if (headerCspan === categoryCspan) {
			for (var categoryIndex = index; categoryIndex < index + headerCspan; categoryIndex++) {
				$categoryCells.eq(categoryIndex).remove();
			}
			$currentHeader.attr('rowspan', 2);
		}
		
		// 結合した製品の列に対する処理をスキップ
		index += headerCspan - 1;
	}
	

	// 製品ごとに性状のテーブルのヘッダー結合
	$headerCells = $('div#HDR_Property table tr:eq(0) th:gt(1)');
	$categoryCells = $('div#HDR_Property table tr:eq(1) td:gt(0)');
	for (var index = 0; index < $headerCells.length; index++) {
		var $currentHeader = $headerCells.eq(index);

		// 製品の列数をカウント、同じ製品のセルを結合する
		var headerCspan = 1;
		if ($currentHeader.html() !== '') {
			$.each($currentHeader.nextAll('th'), function() {
				if ($currentHeader.html() === $(this).html()) {
					$(this).remove();
					headerCspan++;
				}
			});
		}
		$currentHeader.attr('colspan', headerCspan);
		
		// 製品の同列の構成のうち空の値を持つ列数をカウント
		var categoryCspan = 0;
		for (var categoryIndex = index; categoryIndex < index + headerCspan; categoryIndex++) {
			var categoryHtml = $categoryCells.eq(categoryIndex).html();
			if (categoryHtml === '' || categoryHtml === '\x0a') {
				categoryCspan++;
			}
		}
		
		// 製品の列数と空の構成の列数が一致する場合はセルを結合する
		if (headerCspan === categoryCspan) {
			for (var categoryIndex = index; categoryIndex < index + headerCspan; categoryIndex++) {
				$categoryCells.eq(categoryIndex).remove();
			}
			$currentHeader.attr('rowspan', 2);
		}
		
		// 結合した製品の列に対する処理をスキップ
		index += headerCspan - 1;
	}
	


});

// 表の列幅指定を適用する
function setTableColWidth() {
    $.each($.find('table'), function () {
        var tdTag = $(this).find('tbody > tr:last > td[colWidth]');
        // 列幅情報がテーブル内に見つからない場合、列幅指定の対象外となる
        if (!tdTag.length) {
            return true;
        }

        // 列幅情報を配列に格納する
        var widthArray = new Array(tdTag.length);
        $.each(tdTag, function (index, colTag) {
            widthArray[index] = $(colTag).attr('colWidth');
        });
        // テーブルから列幅情報行を削除する
        var lastTr = $(this).find('tbody > tr:last');
        lastTr.remove();

        // 行のリストを取得する
        var $headerRows = $(this).find('thead > tr');
        var $bodyRows = $(this).find('tbody > tr');

        // 行数を求める
        var rowNum = $headerRows.length + $bodyRows.length;

        // 列数を求める
        var $tmpRow = $(this).find('tbody > tr:eq(0)');
        if ($tmpRow.length == 0) {
            $tmpRow = $(this).find('thead > tr:eq(0)');
        }
        var columnNum = 0;
        $.each($tmpRow.children(), function (index, firstRecordCell) {
            var strColspan = $(firstRecordCell).attr('colspan');
            if (strColspan === undefined) {
                // 結合セルでない場合、列数に1を加算する
                columnNum += 1;
            } else {
                // 結合セルの場合、列数にcolspanの値を加算する
                columnNum += +strColspan;
            }
            return;
        });

        // 各セルの幅情報を格納する配列を初期化する
        var cellWidthInfo = new Array();
        for (var i = 0; i < rowNum; i++) {
            var rowArray = new Array(columnNum);
            for (var j = 0; j < columnNum; j++) {
                var widthHash = {};
                widthHash['width'] = widthArray[j];
                widthHash['used'] = false;
                rowArray[j] = widthHash;
            }
            cellWidthInfo[i] = rowArray;
        }

        // 各セルの幅情報を結合セルを考慮して格納する
        // <tr>タグをすべて取得する
        var allRows = $(this).find('tr');
        var idxRow = 0;
        var idxCol = 0;
        for (var i = 0; i < allRows.length; i++) {
            var rowTag = allRows[i];
            var allCells = rowTag.children;
            for (var j = 0; j < allCells.length; j++) {
                var cell = allCells[j];
                // 格納先を探す(既に設定されている場合、右隣へ移動する)
                while (cellWidthInfo[idxRow][idxCol]['used']) {
                    idxCol++;
                }
                // colspan,rowspan情報から格納する範囲を求める
                var colspan = $(cell).attr('colspan');
                var rowspan = $(cell).attr('rowspan');
                var colspanNum = 0;
                var rowspanNum = 0;
                if (colspan === undefined) {
                    colspanNum = 1;
                } else {
                    colspanNum += +colspan;
                }
                if (rowspan === undefined) {
                    rowspanNum = 1;
                } else {
                    rowspanNum += +rowspan;
                }
                // セルにwidth情報を格納する(横結合のセルには格納しない)
                if (colspanNum < 2) {
                    $(cell).css('width', cellWidthInfo[idxRow][idxCol]['width']);
                }
                // セルの領域分使用済みにする
                for (var setRow = 0; setRow < rowspanNum; setRow++) {
                    for (var setCol = 0; setCol < colspanNum; setCol++) {
                        cellWidthInfo[idxRow + setRow][idxCol + setCol]['used'] = true;
                    }
                }
                // 格納後、格納先を右隣へ移動する
                idxCol++;
            }
            // 次の行へ格納先を移動する
            idxRow++;
            idxCol = 0;
        }
    });
}
