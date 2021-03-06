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
    maxZoom: 28,
    updateWhenZooming:false,
    updateWhenIdle: true,
    preferCanvas: true
});

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
                layer = L.tileLayer(response.message[i].path +'/{z}/{x}/{y}.png', {
                    attribution: response.message[i].attribution,
                    minZoom: response.message[i].minZoom,
                    maxZoom: response.message[i].maxZoom,
                    id: 'mapbox.streets',
                    noWrap: true,
                    tms: true
                });
                map.setView(response.message[i].lat_lng, 23);
                window.globals.rasters.push(layer);
                window.globals.layers[response.message[i].name] = layer;
            }
            // Add mapbox to know where the image is
            mapbox = L.tileLayer('https://api.mapbox.com/styles/v1/{id}/tiles/{z}/{x}/{y}?access_token={accessToken}', {
                attribution: 'Map data &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, Imagery © <a href="https://www.mapbox.com/">Mapbox</a>',
                maxZoom: 23,
                id: 'mapbox/satellite-streets-v9',
                tileSize: 512,
                zoomOffset: -1,
                accessToken: 'pk.eyJ1IjoibWFwYm94IiwiYSI6ImNpejY4NXVycTA2emYycXBndHRqcmZ3N3gifQ.rJcFIG214AriISLbB6B5aw'
            })
//            window.globals.layers["mapbox/satellite-streets-v9"] = mapbox;
            mapbox.addTo(map);

            L.control.layers(window.globals.layers, {}).addTo(map);
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
        circle: true
    }
});

drawControl.addTo(map);

draw_shapes = function(geoJson, label_type) {
    geoJson.properties.options.weight = 0.5;
    if (label_type == "circle" || label_type == "Circle") {
        circleLayer = L.circle([geoJson.geometry.coordinates[1], geoJson.geometry.coordinates[0]], geoJson.properties.options);
        drawnItems.addLayer(circleLayer);
    } else if (label_type.toLowerCase() == "rectangle") {
        var rectLayer = L.rectangle([
            [geoJson.geometry.coordinates[0][0].slice().reverse(), geoJson.geometry.coordinates[0][1].slice().reverse(),
                geoJson.geometry.coordinates[0][2].slice().reverse(), geoJson.geometry.coordinates[0][3].slice().reverse()
            ]
        ], geoJson.properties.options);
        drawnItems.addLayer(rectLayer);
    } else if (label_type.toLowerCase() == "polygon") {
        coords = [];
        for (j = 0; j < geoJson.geometry.coordinates.length; j++) {
            coords.push([]);
            for (k = 0; k < geoJson.geometry.coordinates[j].length; k++) {
                coords[j].push(geoJson.geometry.coordinates[j][k].slice().reverse());
            }
        }
        var polyLayer = L.polygon(coords, geoJson.properties.options);
        drawnItems.addLayer(polyLayer);
    } else {
        var geoJsonLayer = L.geoJSON(geoJson, geoJson.properties.options);
        drawnItems.addLayer(geoJsonLayer);
    }
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

            $.ajax({
                url: "/webclient/addTiledLabel",
                type: "POST",
                dataType: "text",
                data: JSON.stringify(requestObj),
                success: function(data) {
                    showSnackBar(JSON.parse(data).message);
                },
                error: function(data) {
                    showSnackBar(JSON.parse(data).message);
                }
            });
            $('#freeHandButton').html('<i class="fa fa-check"></i>Enable Free Hand');
            $('#freeHandButton').removeClass('btn-warning');
            $('#freeHandButton').addClass('btn-success');
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
    layer.addTo(map);
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
//    draw_shapes(geoJson, event.layerType);
    $.ajax({
        url: "/webclient/addTiledLabel",
        type: "POST",
        dataType: "text",
        data: JSON.stringify(requestObj),
        success: function(data) {
            showSnackBar(JSON.parse(data).message);
        },
        error: function(data) {
            showSnackBar(JSON.parse(data).message);
        }
    });

});

map.on('draw:deleted', function(e) {
    var request_obj = [];
    var json = e.layers.toGeoJSON(20);
    e.layers.eachLayer(function(layer) {
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
    $.ajax({
        url: "/webclient/deleteTileLabels",
        type: "POST",
        dataType: "text",
        data: JSON.stringify(request_obj),
        success: function(data) {
            showSnackBar(JSON.parse(data).message);
        },
        error: function(data) {
            showSnackBar(JSON.parse(data).message);
        }
    });
});

window.globals.chart = $("#histogram").get(0).getContext("2d");
var histogram_data = {
    labels: [0, 1, 2, 3, 4, 5, 6, 7],
    datasets: [
        {
            label: "Count per polygon area",
            fill: false,
            lineTension: 0.1,
            backgroundColor: "rgba(75,192,192,0.4)",
            borderColor: "rgba(75,192,192,1)",
            borderCapStyle: 'butt',
            borderDash: [],
            borderDashOffset: 0.0,
            borderJoinStyle: 'miter',
            pointBorderColor: "rgba(75,192,192,1)",
            pointBackgroundColor: "#fff",
            pointBorderWidth: 1,
            pointHoverRadius: 5,
            pointHoverBackgroundColor: "rgba(75,192,192,1)",
            pointHoverBorderColor: "rgba(220,220,220,1)",
            pointHoverBorderWidth: 2,
            pointRadius: 5,
            pointHitRadius: 10,
            data: [0, 0, 0, 0, 0, 0, 0],
        }
    ]
};

window.globals.histogram_chart = Chart.Line(window.globals.chart, {
	data: histogram_data,
    options: {
        showLines: true
    }
});

map.on('moveend', function(e) {
    $.getJSON({
        url: "getAllTiledLabels/?northeast_lat=" + map.getBounds()._northEast.lat.toString() + "&northeast_lng=" + map.getBounds()._northEast.lng.toString() + "&southwest_lat=" + map.getBounds()._southWest.lat.toString() + "&southwest_lng=" + map.getBounds()._southWest.lng.toString(),
        type: "GET",
        success: function(data) {
            geoData = data;
            for(j = 0; j < drawnItems.getLayers().length; j++) {}
                for(i = 0; i < geoData.length; i++) {
                    draw_shapes(geoData[i].geoJSON, geoData[i].label_type)
                }
            }
    });
    bins = $("#customRange2")[0].valueAsNumber;
    $.ajax({
        url: "getHistogramWindow/?northeast_lat=" + map.getBounds()._northEast.lat.toString() + "&northeast_lng=" + map.getBounds()._northEast.lng.toString() + "&southwest_lat=" + map.getBounds()._southWest.lat.toString() + "&southwest_lng=" + map.getBounds()._southWest.lng.toString() + "&number_of_bins=" + bins,
        type: "GET",
        success: function(data) {
            window.globals.histogram_chart.data.labels = data.x;
            window.globals.histogram_chart.data.datasets[0].data = data.y;
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