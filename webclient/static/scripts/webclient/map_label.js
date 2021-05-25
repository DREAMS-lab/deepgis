window.globals = {};
window.globals.rasters = [];
window.globals.layers = {};
window.globals.active_layer = "";

function updateCategoryProperties() {
    $.ajax({
        url: "/webclient/getCategoryInfo",
        type: "GET",
        dataType: "json",
        success: function(response) {
            $('#categories_coll')[0].html = '';
            var output = [];
            window.globals.categoryColor = {};
            for (category in response) {
                cat_list_item = '<li class="grid">' +
                    '<input type="radio" name="category_select" data-color="' + response[category]['color'] + '" value="' + category + '" id="' + category + '">' +
                    '<label for="' + category + '">' + category + '</label>' +
                    '<span class="circle" style="color:' + response[category]['color'] + '; background-color:' + response[category]['color'] +
                    ';"></span></li>';
                output.push(cat_list_item);
                window.globals.categoryColor[response[category]['color']] = category;
            }
            $('#categories_coll').html(output.join(''));

            set_label_draw_color = function() {
                if ($('#freeHandButton').hasClass('btn-warning')) {
                    freeHand();
                    drawer = drawnItems.getLayer(window.globals.lastLayer);
                    drawer.setMode('view');
                } else {
                    var color = rgbToHex($(this).attr('data-color'));
                    drawControl.setDrawingOptions({
                        rectangle: {
                            shapeOptions: {
                                color: color
                            }
                        },
                        circle: {
                            shapeOptions: {
                                color: color
                            }
                        },
                        polygon: {
                            icon: new L.DivIcon({
                                iconSize: new L.Point(4, 4),
                                className: 'leaflet-div-icon leaflet-editing-icon'
                            }),
                            shapeOptions: {
                                color: color,
                                smoothFactor: 0.1
                            }
                        }
                    });
                }
            };
            $("input:radio[name=category_select]").on('change load', set_label_draw_color);
            $("input:radio[name=category_select]:first").attr('checked', true).trigger('change');
        },
        error: function(xhr, errmsg, err) {
            alert(xhr.status + ": " + xhr.responseText);
        }
    });
}

function change_draw_color () {
    if ($('#DrawOrHist').hasClass('btn-danger')) {
        $('#DrawOrHist').removeClass('btn-danger');
        $('#DrawOrHist').addClass('btn-success');
        $('#DrawOrHist').html('<i class="fa fa-check"></i> Plot Histograms');
    } else {
        $('#DrawOrHist').removeClass('btn-success');
        $('#DrawOrHist').addClass('btn-danger');
        $('#DrawOrHist').html('<i class="fa fa-check"></i> Draw objects');
        $("input:radio[name=category_select]:first").attr('checked', true).trigger('change');
    }
};

$('#DrawOrHist').click(change_draw_color);

$('#imagemodal').on('hide.bs.modal', function (e) {
    $('#modal_body').html("");
});

$('#ShowAllHist').click(function () {
    var histogram_count = 1;
    var all_active_layers = drawnItems.getLayers();
    var histograms = {};
    for ( layer in all_active_layers) {
        $('#modal_body').append('<canvas id="histogram' + String(layer) + '" width="600" height="300"></canvas>');
        var chart = $("#histogram" + String(layer)).get(0).getContext("2d");

        current_layer = all_active_layers[layer];
        if (current_layer._layers) {
            current_layer = all_active_layers[layer].getLayers()[0];
        }

        var histogram_data = {
            labels: [0, 1, 2, 3, 4, 5, 6, 7],
            datasets: [
                {
                    label: "Count per rock area for " + current_layer._popup._content,
                    borderColor: "#ff0000",
                    pointBorderColor: "#ff0000",
                    pointBackgroundColor: "#ff0000",
                    pointHoverBackgroundColor: "#ff0000",
                    pointHoverBorderColor: "#ff0000",
                    pointBorderWidth: 1,
                    pointHoverRadius: 1,
                    pointHoverBorderWidth: 1,
                    pointRadius: 3,
                    fill: true,
                    borderWidth: 1,
                    data: [0, 0, 0, 0, 0, 0, 0],
                }
            ]
        };
        var histogram_chart = Chart.Bar(chart, {
            data: histogram_data,
            options: {
                showLines: true,
                scales: {
                    xAxes: [{
                        display: true,
                        scaleLabel: {
                            display: true,
                            labelString: 'Rock area (sq. m)'
                        }
                    }],
                    yAxes: [{
                        display: true,
                        scaleLabel: {
                            display: true,
                            labelString: 'Count'
                        }
                    }]
                }
            }
        });
        bins = $("#customRange2")[0].valueAsNumber;
        var bounds = current_layer.getBounds();
        var ne_lat = bounds._northEast.lat;
        var ne_lng = bounds._northEast.lng;
        var sw_lat = bounds._southWest.lat;
        var sw_lng = bounds._southWest.lng;
        histograms[String(sw_lng) + String(ne_lng) + String(sw_lat) + String(ne_lat)] = histogram_chart;
        $.ajax({
            url: "getHistogramWindow/?northeast_lat=" + ne_lat + "&northeast_lng=" + ne_lng + "&southwest_lat=" + sw_lat + "&southwest_lng=" + sw_lng + "&number_of_bins=" + bins,
            type: "GET",
            success: function(data) {
                histograms[data.unique].data.labels = data.x;
                histograms[data.unique].data.datasets[0].data = data.y;
                histograms[data.unique].update();
            }
        });
        $('#imagemodal').modal('show');
    }
});

function showSnackBar(text) {
    var snackBar = document.getElementById("snackbar");
    snackBar.innerHTML = text;
    // Add the "show" class to DIV
    snackBar.className = "show";
    // After 3 seconds, remove the show class from DIV
    setTimeout(function() {
        snackBar.className = snackBar.className.replace("show", "");
    }, 6000);
}

updateCategoryProperties();


var map = L.map('map', {
    minZoom: 1,
    maxZoom: 22,
    updateWhenZooming:false,
    updateWhenIdle: true,
    preferCanvas: true
});

mapbox = L.tileLayer('https://api.mapbox.com/styles/v1/{id}/tiles/{z}/{x}/{y}?access_token={accessToken}', {
    attribution: 'Map data &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, Imagery © <a href="https://www.mapbox.com/">Mapbox</a>',
    maxZoom: 22,
    id: 'mapbox/satellite-streets-v9',
    tileSize: 512,
    zoomOffset: -1,
    accessToken: 'pk.eyJ1IjoibWFwYm94IiwiYSI6ImNpejY4NXVycTA2emYycXBndHRqcmZ3N3gifQ.rJcFIG214AriISLbB6B5aw'
})

window.globals.layers["mapbox/satellite-streets-v9"] = mapbox;
mapbox.addTo(map);

map.on('baselayerchange', function (e) {
    window.globals.active_layer = e.name;
});

function updateRaster(map) {
    $.ajax({
        url: "/webclient/getRasterInfo",
        type: "GET",
        dataType: "json",
        success: function(response) {
            for (i = 0; i < response.message.length; i++) {
                console.log(response.message[i].path);
                layer = L.tileLayer(response.message[i].path, {
                    attribution: response.message[i].attribution,
                    minZoom: response.message[i].minZoom,
                    maxZoom: response.message[i].maxZoom,
                    id: response.message[i].name,
                    noWrap: true
                });
                window.globals.rasters.push(layer);
                window.globals.layers[response.message[i].name] = layer;
                map.setView(response.message[i].lat_lng, 22);
                window.globals.active_layer = layer;
            }

            geoJson = L.vectorGrid.protobuf("https://rocks-vector-server.deepgis.org/public.webclient_tiledgislabel/{z}/{x}/{y}.pbf", {
                maxNativeZoom: 22,
                vectorTileLayerStyles: {
                    "public.webclient_tiledgislabel": {
                        fillOpacity: 0.05,
                        color: 'red',
                        weight: 0.5,
                        stroke: true,
                        fill: true,
                    }
                },
            }).addTo(map);

            window.globals.rasters.push(geoJson);
            window.globals.layers["prediction"] = geoJson;

            L.control.layers({}, window.globals.layers).addTo(map);
            window.globals.rasters.forEach(function(layer) {
                layer.addTo(map);
            });
        },
        error: function(xhr, errmsg, err) {
            alert(xhr.status + ": " + xhr.responseText);
        }
    });
}

updateRaster(map);

var drawnItems = L.featureGroup().addTo(map);

var drawControl = new L.Control.Draw({
    edit: {
        edit: false,
        remove: true,
        featureGroup: drawnItems,
        poly: {
            allowIntersection: false
        }
    },
    draw: {
        polyline: false,
        marker: false,
        circlemarker: false,
        circle: false
    }
});

drawControl.addTo(map);
var histogram_polygons = 1;

draw_shapes = function(geoJson, label_type) {
    geoJson.properties.options.weight = 0.5;
    if (label_type == "circle" || label_type == "Circle") {
        draw_shapes_layer = L.circle([geoJson.geometry.coordinates[1], geoJson.geometry.coordinates[0]], geoJson.properties.options);
    } else if (label_type.toLowerCase() == "rectangle") {
        var draw_shapes_layer = L.rectangle([
            [geoJson.geometry.coordinates[0][0].slice().reverse(), geoJson.geometry.coordinates[0][1].slice().reverse(),
                geoJson.geometry.coordinates[0][2].slice().reverse(), geoJson.geometry.coordinates[0][3].slice().reverse()
            ]
        ], geoJson.properties.options);
    } else if (label_type.toLowerCase() == "polygon") {
        coords = [];
        for (j = 0; j < geoJson.geometry.coordinates.length; j++) {
            coords.push([]);
            for (k = 0; k < geoJson.geometry.coordinates[j].length; k++) {
                coords[j].push(geoJson.geometry.coordinates[j][k].slice().reverse());
            }
        }
        var draw_shapes_layer = L.polygon(coords, geoJson.properties.options);
    } else {
        draw_shapes_layer = L.geoJSON(geoJson, geoJson.properties.options);
    }
    if ($('#DrawOrHist').hasClass('btn-success')) {
        draw_shapes_layer.bindPopup("Histogram #" + histogram_polygons).openPopup();
        histogram_polygons += 1;
    }
    drawnItems.addLayer(draw_shapes_layer);

    if ($('#DrawOrHist').hasClass('btn-success')) {
        drawnItems.on('click', function(e) {
            bins = $("#customRange2")[0].valueAsNumber;
            var bounds = e.layer.getBounds();
            var ne_lat = bounds._northEast.lat;
            var ne_lng = bounds._northEast.lng;
            var sw_lat = bounds._southWest.lat;
            var sw_lng = bounds._southWest.lng;
            $.ajax({
                url: "getHistogramWindow/?northeast_lat=" + ne_lat + "&northeast_lng=" + ne_lng + "&southwest_lat=" + sw_lat + "&southwest_lng=" + sw_lng + "&number_of_bins=" + bins,
                type: "GET",
                success: function(data) {
                    window.globals.histogram_chart.data.labels = data.x;
                    window.globals.histogram_chart.data.datasets[0].data = data.y;
                    window.globals.histogram_chart.data.datasets[0].borderColor = "#ff0000";
                    window.globals.histogram_chart.data.datasets[0].pointBorderColor = "#ff0000";
                    window.globals.histogram_chart.data.datasets[0].pointBackgroundColor = "#ff0000";
                    window.globals.histogram_chart.data.datasets[0].pointHoverBackgroundColor = "#ff0000";
                    window.globals.histogram_chart.data.datasets[0].pointHoverBorderColor = "#ff0000";
                    window.globals.histogram_chart.data.datasets[0].label = "Count per rock area for " + e.layer._popup._content;
                    window.globals.histogram_chart.update();
                }
            });
        });
    }
    return draw_shapes_layer;
};

function project(lat, lng, zoom) {
    var d = Math.PI / 180,
        max = 1 - 1E-15,
        sin = Math.max(Math.min(Math.sin(lat * d), max), -max),
        scale = 256 * Math.pow(2, zoom);
    var point = {
        x: 1 * lng * d,
        y: 1 * Math.log((1 + sin) / (1 - sin)) / 2
    };
    return point;
}

$('#freeHandButton').click(freeHand);

function freeHand() {
    if ($('#freeHandButton').hasClass('btn-success')) {
        $('#freeHandButton').html('<i class="fa fa-exclamation-triangle"</i>  Disable Free Hand');
        $('#freeHandButton').removeClass('btn-success');
        $('#freeHandButton').addClass('btn-warning');

        var color = rgbToHex($("input:radio[name=category_select]:checked").attr('data-color'));
        var drawer = new L.FreeHandShapes();
        drawer.options = {
            polygon: {
                smoothFactor: 0.000000000001,
                fillOpacity : 0.25,
                noClip : false,
                color: color,
            },
            polyline : {
                color: color,
                opacity: 0.25,
                smoothFactor: 0.000000000001,
                noClip : false,
                clickable : false,
                weight: 1
            },
            simplify_tolerance: 0.000000000001,
            merge_polygons: false,
            concave_polygons: true
        };

        drawer.setMode('add');

        drawer.on('layeradd', function(data) {
            drawer.setMode('view');
            var layer = data.layer;
            var geoJson = layer.toGeoJSON(20);
            var label_type = "polygon";
            var bounds = layer.getBounds();
            var ne_lat = bounds._northEast.lat;
            var ne_lng = bounds._northEast.lng;
            var sw_lat = bounds._southWest.lat;
            var sw_lng = bounds._southWest.lng;
            geoJson.properties.options = layer.options;
            var radio_label_class = $("input:radio[name=category_select]:checked").val();
            requestObj = {
                northeast_lat: ne_lat,
                northeast_lng: ne_lng,
                southwest_lat: sw_lat,
                southwest_lng: sw_lng,
                zoom_level: map.getZoom(),
                label_type: label_type,
                raster: window.globals.active_layer,
                category_name: radio_label_class,
                geoJSON: geoJson
            };

            if ($('#DrawOrHist').hasClass('btn-success')) {
                layer.bindPopup("Histogram #" + histogram_polygons).openPopup();
                histogram_polygons += 1;
                // Case to display histogram
                bins = $("#customRange2")[0].valueAsNumber;
                $.ajax({
                    url: "getHistogramWindow/?northeast_lat=" + ne_lat + "&northeast_lng=" + ne_lng + "&southwest_lat=" + sw_lat + "&southwest_lng=" + sw_lng + "&number_of_bins=" + bins,
                    type: "GET",
                    success: function(data) {
                        window.globals.histogram_chart.data.labels = data.x;
                        window.globals.histogram_chart.data.datasets[0].data = data.y;
                        window.globals.histogram_chart.data.datasets[0].borderColor = "#ff0000";
                        window.globals.histogram_chart.data.datasets[0].pointBorderColor = "#ff0000";
                        window.globals.histogram_chart.data.datasets[0].pointBackgroundColor = "#ff0000";
                        window.globals.histogram_chart.data.datasets[0].pointHoverBackgroundColor = "#ff0000";
                        window.globals.histogram_chart.data.datasets[0].pointHoverBorderColor = "#ff0000";
                        window.globals.histogram_chart.data.datasets[0].label = "Count per rock area for Histogram #" + (histogram_polygons - 1);
                        window.globals.histogram_chart.update();
                        layer.openPopup();
                    }
                });
            } else {
                showSnackBar("Adding objects to database is currently disabled.");
//                $.ajax({
//                    url: "/webclient/addTiledLabel",
//                    type: "POST",
//                    dataType: "text",
//                    data: JSON.stringify(requestObj),
//                    success: function(data) {
//                        showSnackBar(JSON.parse(data).message);
//                    },
//                    error: function(data) {
//                        showSnackBar(JSON.parse(data).message);
//                    }
//                });
            }
            $('#freeHandButton').html('<i class="fa fa-check"></i>Enable Free Hand');
            $('#freeHandButton').removeClass('btn-warning');
            $('#freeHandButton').addClass('btn-success');

            layer.on('click', function(e) {
                bins = $("#customRange2")[0].valueAsNumber;
                var bounds = e.sourceTarget._bounds;
                var ne_lat = bounds._northEast.lat;
                var ne_lng = bounds._northEast.lng;
                var sw_lat = bounds._southWest.lat;
                var sw_lng = bounds._southWest.lng;
                $.ajax({
                    url: "getHistogramWindow/?northeast_lat=" + ne_lat + "&northeast_lng=" + ne_lng + "&southwest_lat=" + sw_lat + "&southwest_lng=" + sw_lng + "&number_of_bins=" + bins,
                    type: "GET",
                    success: function(data) {
                        window.globals.histogram_chart.data.labels = data.x;
                        window.globals.histogram_chart.data.datasets[0].data = data.y;
                        window.globals.histogram_chart.data.datasets[0].borderColor = "#ff0000";
                        window.globals.histogram_chart.data.datasets[0].pointBorderColor = "#ff0000";
                        window.globals.histogram_chart.data.datasets[0].pointBackgroundColor = "#ff0000";
                        window.globals.histogram_chart.data.datasets[0].pointHoverBackgroundColor = "#ff0000";
                        window.globals.histogram_chart.data.datasets[0].pointHoverBorderColor = "#ff0000";
                        window.globals.histogram_chart.data.datasets[0].label = "Count per rock area for " + e.sourceTarget._popup._content;
                        window.globals.histogram_chart.update();
                    }
                });
            });
        });
        drawnItems.addLayer(drawer);
        window.globals.lastLayer = drawnItems.getLayerId(drawer);
    } else {
        $('#freeHandButton').html('<i class="fa fa-check"></i>Enable Free Hand');
        $('#freeHandButton').removeClass('btn-warning');
        $('#freeHandButton').addClass('btn-success');
    }
}

map.on(L.Draw.Event.CREATED, function(event) {
    var layer = event.layer;
    var geoJson = layer.toGeoJSON(20);
    geoJson.properties.options = layer.options;
    var ne_lat;
    var ne_lng;
    var sw_lat;
    var sw_lng;
    if (window.globals.active_layer == "") {
        showSnackBar("No active raster layer present.");
        return;
    }
    var bounds = layer.getBounds();
    ne_lat = bounds._northEast.lat;
    ne_lng = bounds._northEast.lng;
    sw_lat = bounds._southWest.lat;
    sw_lng = bounds._southWest.lng;
    var radio_label_class = $("input:radio[name=category_select]:checked").val();
    requestObj = {
        northeast_lat: ne_lat,
        northeast_lng: ne_lng,
        southwest_lat: sw_lat,
        southwest_lng: sw_lng,
        zoom_level: map.getZoom(),
        label_type: event.layerType,
        category_name: radio_label_class,
        raster: window.globals.active_layer,
        geoJSON: geoJson
    };
    var _layer = draw_shapes(geoJson, event.layerType);

    if ($('#DrawOrHist').hasClass('btn-success')) {
        // Case to display histogram
        bins = $("#customRange2")[0].valueAsNumber;
        $.ajax({
            url: "getHistogramWindow/?northeast_lat=" + ne_lat + "&northeast_lng=" + ne_lng + "&southwest_lat=" + sw_lat + "&southwest_lng=" + sw_lng + "&number_of_bins=" + bins,
            type: "GET",
            success: function(data) {
                window.globals.histogram_chart.data.labels = data.x;
                window.globals.histogram_chart.data.datasets[0].data = data.y;
                window.globals.histogram_chart.data.datasets[0].borderColor = "#ff0000";
                window.globals.histogram_chart.data.datasets[0].pointBorderColor = "#ff0000";
                window.globals.histogram_chart.data.datasets[0].pointBackgroundColor = "#ff0000";
                window.globals.histogram_chart.data.datasets[0].pointHoverBackgroundColor = "#ff0000";
                window.globals.histogram_chart.data.datasets[0].pointHoverBorderColor = "#ff0000";
                window.globals.histogram_chart.data.datasets[0].label = "Count per rock area for Histogram #" + (histogram_polygons - 1);
                window.globals.histogram_chart.update();
                _layer.openPopup();
            }
        });
    } else {
        showSnackBar("Adding objects to database is currently disabled.");
        // Case to draw objects
        // $.ajax({
        //     url: "/webclient/addTiledLabel",
        //     type: "POST",
        //     dataType: "text",
        //     data: JSON.stringify(requestObj),
        //     success: function(data) {
        //         showSnackBar(JSON.parse(data).message);
        //     },
        //     error: function(data) {
        //         showSnackBar(JSON.parse(data).message);
        //     }
        // });
    }
});

map.on('draw:deleted', function(e) {
    var request_obj = [];
    var json = e.layers.toGeoJSON(20);

    e.layers.eachLayer(function(layer) {
        drawnItems.removeLayer(layer);
        if (layer instanceof L.Rectangle) {
            var label_type = "rectangle";
        } else if (layer instanceof L.Circle) {
            //Workaround from https://github.com/Leaflet/Leaflet.draw/issues/701
            layer._map = layer._map || map;
            var label_type = "circle";
        } else if (layer instanceof L.Polygon) {
            var label_type = "polygon";
        } else {
            return; //Not one of the possible label types
        }

        var bounds = layer.getBounds();
        var jsonMessage = JSON.stringify(layer.toGeoJSON(20));
        var northeast = bounds.getNorthEast();
        var southwest = bounds.getSouthWest();
        delete_layer_dict = {
            northeast_lat: northeast.lat,
            northeast_lng: northeast.lng,
            southwest_lat: southwest.lat,
            southwest_lng: southwest.lng,
            label_type: label_type,
            geoJSON: jsonMessage,
            category_name: window.globals.categoryColor[hexToRgb(layer.options.color)]
        };

        request_obj.push(delete_layer_dict);

        if (layer._map != null) {
            layer._map.removeLayer(layer);
        }

    });

    // $.ajax({
    //     url: "/webclient/deleteTileLabels",
    //     type: "POST",
    //     dataType: "text",
    //     data: JSON.stringify(request_obj),
    //     success: function(data) {
    //         showSnackBar(JSON.parse(data).message);
    //     },
    //     error: function(data) {
    //         showSnackBar(JSON.parse(data).message);
    //     }
    // });
});

window.globals.chart = $("#histogram").get(0).getContext("2d");

var histogram_data = {
    labels: [0, 1, 2, 3, 4, 5, 6, 7],
    datasets: [
        {
            label: "Count per rock area in the current view window",
            borderColor: "#ff0000",
            pointBorderColor: "#ff0000",
            pointBackgroundColor: "#ff0000",
            pointHoverBackgroundColor: "#ff0000",
            pointHoverBorderColor: "#ff0000",
            pointBorderWidth: 1,
            pointHoverRadius: 1,
            pointHoverBorderWidth: 1,
            pointRadius: 3,
            fill: true,
            borderWidth: 1,
            data: [0, 0, 0, 0, 0, 0, 0],
        }
    ]
};

window.globals.histogram_chart = Chart.Bar(window.globals.chart, {
	data: histogram_data,
    options: {
        showLines: true,
        scales: {
            xAxes: [{
                display: true,
                scaleLabel: {
                    display: true,
                    labelString: 'Rock area (sq. m)'
                }
            }],
            yAxes: [{
                display: true,
                scaleLabel: {
                    display: true,
                    labelString: 'Count'
                }
            }]
        }
    }
});

map.on('moveend', function(e) {
    bins = $("#customRange2")[0].valueAsNumber;
    $.ajax({
        url: "getHistogramWindow/?northeast_lat=" + map.getBounds()._northEast.lat.toString() + "&northeast_lng=" + map.getBounds()._northEast.lng.toString() + "&southwest_lat=" + map.getBounds()._southWest.lat.toString() + "&southwest_lng=" + map.getBounds()._southWest.lng.toString() + "&number_of_bins=" + bins,
        type: "GET",
        success: function(data) {
            window.globals.histogram_chart.data.labels = data.x;
            window.globals.histogram_chart.data.datasets[0].data = data.y;
            window.globals.histogram_chart.data.datasets[0].borderColor = "#ff0000";
            window.globals.histogram_chart.data.datasets[0].pointBorderColor = "#ff0000";
            window.globals.histogram_chart.data.datasets[0].pointBackgroundColor = "#ff0000";
            window.globals.histogram_chart.data.datasets[0].pointHoverBackgroundColor = "#ff0000";
            window.globals.histogram_chart.data.datasets[0].pointHoverBorderColor = "#ff0000";
            window.globals.histogram_chart.data.datasets[0].label = "Count per rock area in the current view window";
            window.globals.histogram_chart.update();
        }
    });

});

$("#customRange2").on( "click", function() {
    bins = $("#customRange2")[0].valueAsNumber;
    $("#customRange2label").text("Histogram Bins: " + $("#customRange2")[0].value);
    $.ajax({
        url: "getHistogramWindow/?northeast_lat=" + map.getBounds()._northEast.lat.toString() + "&northeast_lng=" + map.getBounds()._northEast.lng.toString() + "&southwest_lat=" + map.getBounds()._southWest.lat.toString() + "&southwest_lng=" + map.getBounds()._southWest.lng.toString() + "&number_of_bins=" + bins,
        type: "GET",
        success: function(data) {
            window.globals.histogram_chart.data.labels = data.x;
            window.globals.histogram_chart.data.datasets[0].data = data.y;
            window.globals.histogram_chart.data.datasets[0].borderColor = "#ff0000";
            window.globals.histogram_chart.data.datasets[0].pointBorderColor = "#ff0000";
            window.globals.histogram_chart.data.datasets[0].pointBackgroundColor = "#ff0000";
            window.globals.histogram_chart.data.datasets[0].pointHoverBackgroundColor = "#ff0000";
            window.globals.histogram_chart.data.datasets[0].pointHoverBorderColor = "#ff0000";
            window.globals.histogram_chart.data.datasets[0].label = "Count per rock area in the current view window";
            window.globals.histogram_chart.update();
        }
    });
});

$("#category_submit").click(function() {
    $("#category_submit").attr("disabled", true);
    if ($("#add_new_category").val()) {
        $.post("/webclient/addCategory", {
            data: $("#add_new_category").val()
        }).done(function(data) {
            if (data.result == "failure") {
                showSnackBar(data.reason);
            };
            if (data.result == "success") {
                cat_list_item = '<li class="grid">' +
                    '<input type="radio" name="category_select" value="' + data.data + '" id="' + data.data + '">' +
                    '<label for="' + data.data + '">' + data.data + '</label>' +
                    '<span class="circle" style="color:' + data.color + '; background-color:' +
                    data.color + ';"></span></li>';

                $('#categories_coll').append($(cat_list_item));
                showSnackBar("Successfully added " + data.data + " to Categories");

                updateCategoryProperties();
                var inputField = document.getElementById("add_new_category");

                inputField.value = "";
            };
        });
    } else {
        alert("Missing category name.");
    }
    $("#category_submit").attr("disabled", false);
});

function hexToRgb(hex) {
    var result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? "rgb(" + parseInt(result[1], 16) + ", " + parseInt(result[2], 16) + ", " + parseInt(result[3], 16) + ")" : null;
}

function componentToHex(i) {
    var c = parseInt(i);
    var hex = c.toString(16);
    return hex.length == 1 ? "0" + hex : hex;
}

function rgbToHex(i) {
    var regex = /\d+/g;
    var result = i.match(regex);
    return "#" + componentToHex(result[0]) + componentToHex(result[1]) + componentToHex(result[2]);
}

change_draw_color();
change_draw_color();