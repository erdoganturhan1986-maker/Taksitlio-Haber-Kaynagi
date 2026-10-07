var urlObject = new Object();
urlObject.ParaBirimiGetirUrl = undefined;

var metinObject = new Object();

var valuesObject = new Object();
valuesObject.IlkAcilacakTablo = 10001;




function SeciliTabloDegisti() {

    var tabloNo = $('#TabloListesi').val();

    $.getJSON(urlObject.ParaBirimiGetirUrl, { tabloNo: tabloNo }, function (paraBirimleri) {
        var birimSelect = $('#ddlParaBirimi');
        birimSelect.empty();
        $.each(paraBirimleri, function (index, birim) {
            birimSelect.append(
                $('<option/>')
                    .attr('value', birim.Id)
                    .text(birim.Name)
            );
            birimSelect.val('TL').trigger('chosen:updated');
            birimSelect.change();
        });
    });
    RaporGetir("#grdRapor", "#pager", "#lblUyari", "#lblDuyuru");
}

function YenidenYukle() {
    RaporGetir("#grdRapor", "#pager", "#lblUyari", "#lblDuyuru");
}

function TabloDegistir(tabloValue) {

    $("#TabloListesi").val(tabloValue);
    RaporGetir("#grdRapor", "#pager", "#lblUyari", "#lblDuyuru");
    $(".tabloListesiItem").each(function () {
        $(this).removeClass("activatedItem");
    });
    $("#tabloListesiItem-" + tabloValue).addClass("activatedItem");
}

function SecilenKalemSutunGetir(nodes, checkedNodes) {
    for (var i = 0; i < nodes.length; i++) {
        if (nodes[i].checked) {
            checkedNodes.push(nodes[i].id);
        } else if (nodes[i].hasChildren) {
            SecilenKalemSutunGetir(nodes[i].children.view(), checkedNodes);
        }
    }
}


function KalemEkleKaldir(id) {

    $('#ddlTabloKalem option').each(function () {
        if (this.value === id) {
            if (this.selected) {
                $(this).prop("selected", false);
            }
            else {
                $(this).prop("selected", true);
            }
        }
    });

    $('#ddlTabloKalem').trigger('chosen:updated');

    KalemSutunGoster();
}


function RaporGetir(gridRapor, pager, lblUyari, lblDuyuru) {
    overlayOn();
    $("#Bekleyiniz").show();


    var seciliTabloNo = $('#TabloListesi').val();
    var seciliYil = $('#ddlYil').val();
    var seciliAy = $('#ddlAy').val();
    var seciliParaBirimi = $('#ddlParaBirimi').val();
    var seciliTaraf = [];
    seciliTaraf = $('#ddlTaraf').val();

    if (seciliTaraf !== null) {
        $(lblUyari).html("");
        $(lblDuyuru).html("");
        $(gridRapor).jqGrid('GridUnload');
        $.ajax(
            {
                type: 'POST',
                url: urlObject.BasitRaporGetirUrl,
                data: { tabloNo: seciliTabloNo, yil: seciliYil, ay: seciliAy, paraBirimi: seciliParaBirimi, 'taraf': seciliTaraf },
                dataType: "json",
                traditional: true,
                success: function (result) {
                    $("#Bekleyiniz").hide();

                    if (!result.success) {
                        alert(result.error);
                    } else {
                        var colModels = result.Json.colModels;
                        var colNames = result.Json.colNames;
                        var caption = result.Json.caption;
                        var data = result.Json.data;
                        var uyari = result.Json.uyari;
                        var duyuruList = result.Json.duyurular;
                        $("#divRapor").show();
                        $(gridRapor).jqGrid({
                            datatype: 'jsonstring',
                            datastr: data,
                            colNames: colNames,
                            colModel: colModels,
                            jsonReader: {
                                root: 'rows',
                                repeatitems: true
                            },
                            grouping: true,
                            groupingView: { groupField: ['BankaAdi'], groupColumnShow: false, groupCollapse: false, plusicon: 'ui-icon-circle-plus', minusicon: 'ui-icon-circle-minus' },
                            gridview: true,
                            pager: $(pager),
                            rowNum: 840,
                            rowList: [30, 60, 120, 240, 480, 840],
                            loadComplete: function () {
                                $("#btnExcel").find(".ui-icon").css({ "background-image": "Url(" + urlObject.ExcelIconUrl + ")", "background-position": "left" });
                                $("#btnPdf").find(".ui-icon").css({ "background-image": "Url(" + urlObject.PdfIconUrl + ")", "background-position": "right" });
                            },
                            viewrecords: true,
                            autowidth: true,
                            height: '100%',
                            rowattr: function (rd) {
                                //                    if (rd.parent === "null")
                                if (rd.BasitFont === "bold") {
                                    return { "class": "BoldSatir" };
                                }
                                if (rd.BasitFont === "italic") {
                                    return { "class": "ItalicSatir" };
                                }
                            },
                            //        rownumbers: true,
                            caption: caption,

                            sortname: 'BasitSira',
                            sortorder: "asc"
                            //   shrinkToFit: true,
                            //                  footerrow: false
                        }); //end jqgrid
                        $(lblUyari).html(uyari);
                        $(lblDuyuru).html(duyuruList);
                        $(gridRapor).jqGrid('navGrid', pager, { add: false, edit: false, del: false, search: false, refresh: false },
                            {}, {}, {}, {}, {});

                        $(gridRapor).jqGrid('navButtonAdd', pager, {
                            caption: '<span class="ui-pg-button-text">' + metinObject.ExcelDil + '</span>',
                            id: "btnExcel",
                            buttonicon: "ui-icon-bookmark",
                            onClickButton: function () {
                                var tarafNesne = {};
                                for (var i = 0; i < seciliTaraf.length; i++) {
                                    tarafNesne[i] = seciliTaraf[i];
                                }
                                window.location = urlObject.BasitExcelAktarUrl + '?' +
                                    $.param({
                                        tabloNo: seciliTabloNo,
                                        yil: seciliYil,
                                        ay: seciliAy,
                                        paraBirimi: seciliParaBirimi,
                                        'taraf': tarafNesne
                                    });
                            }
                        });
                        $(gridRapor).jqGrid('navButtonAdd', pager, {
                            caption: '<span class="ui-pg-button-text">' + metinObject.PdfDil + '</span>',
                            id: "btnPdf",
                            buttonicon: "ui-icon-bookmark",
                            onClickButton: function () {
                                window.location = urlObject.BasitPdfIndirUrl + '?' +
                                    $.param({
                                        tabloNo: seciliTabloNo,
                                        dosyaAdi: metinObject.PdfDil
                                    });
                            }
                        });
                        $(gridRapor).trigger('reloadGrid');
                    }

                    overlayOff();
                }
            }); //end ajax
    }
    else {
        if ($('#lblTaraf').text().indexOf("Taraf") !== -1)
            alert("Taraf bilgisi seçmediniz!");
        else
            alert("You did not choose any group!");
    }
}



function KalemSutunGoster()
{
    var treeView = $("#tvKalemSutun").data("kendoTreeView");
    if (treeView !== null) treeView.destroy();
    var seciliKalem = [];
    seciliKalem = $('#ddlTabloKalem').val();

    jQuery.ajaxSettings.traditional = true;

    $.getJSON(urlObject.KalemSutunGetir,{
            kalemNoList: seciliKalem
        }, function (data) {

            $("#tvKalemSutun").kendoTreeView({
                checkboxes: {
                    checkChildren: true
                }
            });

            if (data[0].text !== null) $("#tvKalemSutun").data("kendoTreeView").setDataSource(data);
            else {
                $("#tvKalemSutun").data("kendoTreeView").destroy();
            }
        });
}

function TarafEklenmemisseEkle(id) {

    $('#ddlTaraf option').each(function () {
        if (this.value === id) {
            if (this.selected === true);
            else {
                $(this).prop("selected", true);
            }
        }
    });
  
    $('#ddlTaraf').trigger('chosen:updated');
}