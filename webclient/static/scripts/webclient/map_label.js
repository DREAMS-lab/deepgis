window.globals = {};
//function to update category properties when new categories are added
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
                    drawnItems.removeLayer(window.globals.lastLayer);
                    freeHand();
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

// Add categories to the main page
updateCategoryProperties();

var raster1 = L.tileLayer('/static/outputfolder1/{z}/{x}/{y}.png', {
    attribution: 'ASU, Ramon Arrowsmith',
    minZoom: 1,
    maxZoom: 7,
    noWrap: true,
    id: 'mapbox.streets',
    tms: true
});

var map = L.map('map', {
    center: [39.73, -104.99],
    minZoom: 1,
    maxZoom: 7,
    layers: [raster1],
    updateWhenZooming:false,
    updateWhenIdle: true,
    preferCanvas: true
});

map.setView([-50, -50], 2);

var baseLayers = {
    "Raster 1": raster1,
};


L.control.layers(baseLayers, {}).addTo(map);

var drawnItems = L.featureGroup().addTo(map);

L.EditToolbar.Delete.include({
    removeAllLayers: false
});

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

draw_shapes = function(geoJson, label_type) {
    geoJson.properties.options.weight = 0.5;
    if (label_type == "circle") {
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

$.getJSON({
    url: "get_all_tiled_labels/?northeast_lat=" + map.getBounds()._northEast.lat.toString() + "&northeast_lng=" + map.getBounds()._northEast.lng.toString() + "&southwest_lat=" + map.getBounds()._southWest.lat.toString() + "&southwest_lng=" + map.getBounds()._southWest.lng.toString(),
    type: "GET",
    success: function(data) {
        geoData = data;
        for (i = 0; i < geoData.length; i++) {
            draw_shapes(geoData[i].geoJSON, geoData[0].geoJSON.type)
        }
    }
});


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
        var drawer = new L.FreeHandShapes({
            polygon: {
                color: color,
                weight: 0.5,
                fillOpacity: 0.25,
                smoothFactor: 0.01,
                noClip: false
            }
        });

        drawer.setMode('add');
        drawer.on('layeradd', function(data) {
            drawer.setMode('view');
            var layer = data.layer;
            var geoJson = layer.toGeoJSON();
            var label_type = "polygon";
            var bounds = layer.getBounds();
            var ne_lat = layer._bounds._northEast.lat;
            var ne_lng = layer._bounds._northEast.lng;
            var sw_lat = layer._bounds._southWest.lat;
            var sw_lng = layer._bounds._southWest.lng;
            geoJson.properties.options = layer.options;
            var radio_label_class = $("input:radio[name=category_select]:checked").val();
            console.log(radio_label_class);
            requestObj = {
                northeast_lat: ne_lat,
                northeast_lng: ne_lng,
                southwest_lat: sw_lat,
                southwest_lng: sw_lng,
                zoom_level: map.getZoom(),
                label_type: label_type,
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
    var geoJson = layer.toGeoJSON();
    var ne_lat;
    var ne_lng;
    var sw_lat;
    var sw_lng;
    var propJSON = {};

    if (event.layerType == "circle") {
        layer.addTo(map);
        var bounds = layer.getBounds();
        layer.removeFrom(map);
        var northeast = bounds.getNorthEast();
        var southwest = bounds.getSouthWest();
        ne_lat = layer._latlng.lat + layer._mRadius;
        ne_lng = layer._latlng.lng + layer._mRadius;
        sw_lat = layer._latlng.lat - layer._mRadius;
        sw_lng = layer._latlng.lng - layer._mRadius;
        propJSON.latlng = layer._latlng;
        propJSON.radius = layer._mRadius;
        geoJson.properties.shape_type = "circle";
        geoJson.properties.radius = layer._mRadius;
    } else {
        var bounds = layer.getBounds();
        ne_lat = layer._bounds._northEast.lat;
        ne_lng = layer._bounds._northEast.lng;
        sw_lat = layer._bounds._southWest.lat;
        sw_lng = layer._bounds._southWest.lng;
        propJSON.latlngs = layer._latlngs[0];
    }
    //layer.options.weight = 0.5;
    geoJson.properties.options = layer.options;
    var radio_label_class = $("input:radio[name=category_select]:checked").val();
    requestObj = {
        northeast_lat: ne_lat,
        northeast_lng: ne_lng,
        southwest_lat: sw_lat,
        southwest_lng: sw_lng,
        zoom_level: map.getZoom(),
        label_type: event.layerType,
        category_name: radio_label_class,
        geoJSON: geoJson
    };
    draw_shapes(geoJson, event.layerType);
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
    console.log(e);
    var request_obj = [];
    var json = e.layers.toGeoJSON();
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
        var jsonMessage = JSON.stringify(layer.toGeoJSON());
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