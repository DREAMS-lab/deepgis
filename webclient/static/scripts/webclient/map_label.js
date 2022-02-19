// DO python manage.py collectstatic AFTER MAKING CHANGES, SINCE IT'S A STATIC FILE

window.globals = {};
window.globals.rasters = [];
window.globals.layers = {};
window.globals.active_layer = "";

function updateCategoryProperties() {
    // Category Properties include color and name of the category
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
            // set color of the FreeHand and Leaflet draw options to the color of the category selected
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

// There are two modes of workflow: plot histograms and draw objects.
// Decision on which mode is currently active is made based on which 
// btn-* CSS class is active on the toggle button.
function change_draw_color () {
    // Switch between Plot Histograms and Draw objects
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

// Toggle mode on click
$('#DrawOrHist').click(change_draw_color);

$('#imagemodal').on('hide.bs.modal', function (e) {
    $('#modal_body').html("");
});

// $(document).ready(function(){
//     $("#exampleModal").modal('show');
// });

// Display all the drawn histograms in a single pop-up (modal) window for comparison. 
$('#ShowAllHist').click(function () {
    var histogram_count = 1;
    var all_active_layers = drawnItems.getLayers();
    var histograms = {};
    for ( layer in all_active_layers) {
        current_layer = all_active_layers[layer];
        // HACK: if current_layer has _layer, it's a collection of layers; get the 0th layer then.
        if (current_layer._layers) { 
            current_layer = all_active_layers[layer].getLayers()[0];
        }
        if (current_layer._popup === undefined) {
            continue;
        }
        // Base histogram data, will be updated later
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

        $('#modal_body').append('<canvas id="histogram' + String(layer) + '" width="600" height="300"></canvas>');
        var chart = $("#histogram" + String(layer)).get(0).getContext("2d");

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
                console.log(data);
                histograms[data.unique].data.labels = data.x;
                histograms[data.unique].data.datasets[0].data = data.y;
                histograms[data.unique].update();
            }
        });
        $('#imagemodal').modal('show');
    }
});

// Show snackbar for the text provided
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

// var tileSize = 256;

// L.Control.Layers.prototype._addItem = function(obj) {

//     var label = document.createElement('label'),
//         input,
//         checked = this._map.hasLayer(obj.layer);

//     if (obj.overlay) {
//         input = document.createElement('input');
//         input.type = 'checkbox';
//         input.className = 'leaflet-control-layers-selector';
//         input.defaultChecked = checked;
//     }
//     else {
//         input = this._createRadioElement('leaflet-base-layers', checked);
//     }

//     input.layerId = L.stamp(obj.layer);

//     L.DomEvent.on(input, 'click', this._onInputClick, this);

//     var name = document.createElement('span');
//     name.innerHTML = ' ' + obj.name;

//     label.appendChild(input);
//     label.appendChild(name);
//     label.className = obj.overlay ? "checkbox" : "radio";
//     var container = obj.overlay ? this._overlaysList : this._baseLayersList;
//     container.appendChild(label);

//     return label;
// }

var map = L.map('map', {
    minZoom: 1,
    maxZoom: 22,
    updateWhenZooming:false,
    updateWhenIdle: true,
    preferCanvas: true
});

var options = {
    onEachFeature: function(feature, layer) {
        if (feature.properties) {
            layer.bindPopup(Object.keys(feature.properties).map(function(k) {
                if(k === '__color__'){
                    return;
                }
                return k + ": " + feature.properties[k];
            }).join("<br />"), {
                maxHeight: 200
            });
        }
    },
    style: function(feature) {
        return {
            opacity: 1,
            fillOpacity: 0.7,
            radius: 6,
            color: feature.properties.__color__
        }
    },
    pointToLayer: function(feature, latlng) {
        return L.circleMarker(latlng, {
            opacity: 1,
            fillOpacity: 0.7,
            color: feature.properties.__color__
        });
    }
};

// Base map layer is a Mapbox API layer for visualization of the location
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

/*
var shpfile = new L.Shapefile('static/zipped_shpfile/maSP.zip', {
    onEachFeature: function(feature, layer) {
        if (feature.properties) {
            layer.bindPopup(Object.keys(feature.properties).map(function(k) {
                return k + ": " + feature.properties[k];
            }).join("<br />"), {
                maxHeight: 200
            });
        }
    }
});

shpfile.addTo(map);
shpfile.once("data:loaded", function() {
    console.log("finished loaded shapefile");
});
*/


// var geojsonFeature = {
//     "type": "Feature",
//     "properties": {"party": "Republican"},
//     "geometry": {
//         "type": "Polygon",
//         "coordinates": [[
//             [-104.05, 48.99],
//             [-97.22,  48.98],
//             [-96.58,  45.94],
//             [-104.03, 45.94],
//             [-104.05, 48.99]
//         ]]
//     }
// };
// L.geoJSON(geojsonFeature).addTo(map);


// var vector_tile = L.tileLayer(
//     'https://rocks-raster-tile-server.deepgis.org/data/merged_crowns/{z}/{x}/{y}.pbf', 
//     { attribution: 'ASU'});
    
// vector_tile.addTo(map);

// var vector_tile = L.vectorGrid.protobuf(
//     "https://rocks-raster-tile-server.deepgis.org/data/merged_crowns/{z}/{x}/{y}.pbf", {
//                 maxNativeZoom: 20,
//                 // vectorTileLayerStyles: {
//                 //     "public.webclient_tiledgislabel": {
//                 //         fillOpacity: 0.05,
//                 //         color: 'red',
//                 //         weight: 0.5,
//                 //         stroke: true,
//                 //         fill: true,
//                 //     }
//                 // },
//             });
// console.log("vector tile is", vector_tile);
// vector_tile.addTo(map);




// shp("http://localhost:8273/webclient/static/shp_file/TOWNSSURVEY_POLYM").then(function(geojson){
//     //do something with your geojson
//     console.log("This function ran");
//     console.log(geojson);
//     L.geoJSON(geojson).addTo(map);
// });

// console.log(window. location);

// //webclient/static/scripts/webclient/map_label.js
// shp("../../shp_file/CONGRESS113_POLY").then(function(geojson){
//     //do something with your geojson
//     console.log("2nd function ran");
//     console.log(geojson);
// });

// Display all raster objects in the database from their corresponding path to tile PNGs.
function updateRaster(map, image_name = 'Landsat', comma_sep_bands = '1,2,3') {
    $.ajax({
        url: "/webclient/getRasterInfo",
        data: { "image_name": image_name, "comma_sep_bands": comma_sep_bands},
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
                var minZoom = response.message[i].minZoom;
                var maxZoom = response.message[i].maxZoom;

                window.globals.rasters.push(layer);
                window.globals.layers[response.message[i].name] = layer;
                map.setView(response.message[i].lat_lng, maxZoom);
                window.globals.active_layer = layer;
            }
/* 
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
*/
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

updateRaster(map, null, null);
// drawnItems will contain all the drawn features on the map.
var drawnItems = L.featureGroup().addTo(map);

/*
var fragmentShader = `
void main(void) {
    vec4 texelColour = texture2D(uTexture0, vec2(vTextureCoords.s, vTextureCoords.t));
	gl_FragColor = texelColour;
}       
`;

console.log("the code runs");

var antitoner = L.tileLayer.gl({
    fragmentShader: fragmentShader,
    tileUrls: [
        'https://rocks-raster-tile-server.deepgis.org/data/Landsat_1/{z}/{x}/{y}.png'
    ]
}).addTo(map);

//https://rocks-raster-tile-server.deepgis.org/data/Landsat_1.json

console.log("the code is running");
*/

var fragmentShader = `
void main(void) {
	vec4 texelColour_layer1 = texture2D(uTexture0, vec2(vTextureCoords.s, vTextureCoords.t));
	vec4 texelColour_layer2 = texture2D(uTexture1, vec2(vTextureCoords.s, vTextureCoords.t));
    vec4 texelColour_layer3 = texture2D(uTexture1, vec2(vTextureCoords.s, vTextureCoords.t));
    
    float layer1Red   = texelColour_layer1.r; // visible red
	float layer2Green = texelColour_layer2.g; // visible green
	float layer3Blue  = texelColour_layer3.b; // visible blue

	gl_FragColor = vec4(layer1Red, layer2Green, layer3Blue, 1.0);
}       
`;

var RGB_tileUrls = [
    'https://rocks-raster-tile-server.deepgis.org/data/Landsat_1/{z}/{x}/{y}.png',
    'https://rocks-raster-tile-server.deepgis.org/data/Landsat_2/{z}/{x}/{y}.png',
    'https://rocks-raster-tile-server.deepgis.org/data/Landsat_3/{z}/{x}/{y}.png'
];

function runRGB_FalseColor_WebGL(){
    console.log('ran runRGB_FalseColor_WebGL code');
    var antitoner = L.tileLayer.gl({
        fragmentShader: fragmentShader,
        tileUrls: RGB_tileUrls
    }).addTo(map);
};

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

//Function for drawing shapes on the map using geoJson and label_type
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
    // Attach a unique ID to this layer if the mode is in Plot Histogram.
    if ($('#DrawOrHist').hasClass('btn-success')) {
        draw_shapes_layer.bindPopup("Histogram #" + histogram_polygons).openPopup();
        histogram_polygons += 1;
    }
    drawnItems.addLayer(draw_shapes_layer);
   
    // Plot histogram at the bottom of the page for the selected drawn item.
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
        
        if($("input:radio[name=category_select]:checked").val() === undefined) {
            showSnackBar("Missing selection of category");
            return;
        }

        var color = rgbToHex($("input:radio[name=category_select]:checked").attr('data-color'));
        var drawer = new L.FreeHandShapes();
        drawer.options = {
            polygon: {
                smoothFactor: 0.000000000001, // precision for lat and lon
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
            simplify_tolerance: 0.000000000001, // precision for lat and lon
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
                raster: window.globals.active_layer.options.id, // name of the raster image
                category_name: radio_label_class,
                geoJSON: geoJson
            };
            
            if ($('#DrawOrHist').hasClass('btn-success')) {
                layer.bindPopup("Histogram #" + histogram_polygons).openPopup();
                histogram_polygons += 1;
                // Display histogram
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
            } else {
                // Add the annotation as TiledGISLabel
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
            }
            $('#freeHandButton').html('<i class="fa fa-check"></i>Enable Free Hand');
            $('#freeHandButton').removeClass('btn-warning');
            $('#freeHandButton').addClass('btn-success');

        });
        drawnItems.addLayer(drawer);
        window.globals.lastLayer = drawnItems.getLayerId(drawer);
    } else {
        // Toggle the button from enable option to disable option
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
        raster: window.globals.active_layer.options.id,
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
        showSnackBar("Adding objects to database is currently enabled.");
        // Case to draw objects
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
            // Workaround from https://github.com/Leaflet/Leaflet.draw/issues/701
            layer._map = layer._map || map;
            var label_type = "circle";
        } else if (layer instanceof L.Polygon) {
            var label_type = "polygon";
        } else {
            return; // Not one of the possible label types
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
    // This will delete the drawn labels from database.
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
                }
            ]
        }
    }
});

map.on('moveend', function(e) {
    // Load annotations from the database
    $.getJSON({
        url: "getAllTiledLabels/?northeast_lat=" + map.getBounds()._northEast.lat.toString() + "&northeast_lng=" + map.getBounds()._northEast.lng.toString() + "&southwest_lat=" + map.getBounds()._southWest.lat.toString() + "&southwest_lng=" + map.getBounds()._southWest.lng.toString(),
        type: "GET",
        success: function(data) {
            geoData = data;
            for(j = 0; j < drawnItems.getLayers().length; j++) {}
            for(i = 0; i < geoData.length; i++) {
                draw_shapes(geoData[i].geoJSON, geoData[i].geoJSON.type)
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
// Update histogram when user changes the bin size
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

// Creation of new categories
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


/*
Action when person clicks on RGB False color button
*/
$("#RGB_false_color").click(function() {
    console.log("RGB False color button was clicked");

    var image_selected = $( "#image_select option:checked" ).val();
    var red_band = $('#red_band').val()
    var green_band = $('#green_band').val()
    var blue_band = $('#blue_band').val()

    console.log(image_selected);
    console.log(red_band);
    console.log(green_band);
    console.log(blue_band);
    
    $.get( "getRGB_bandsFalseColor", { 
        "image_selected": image_selected,"red_band": red_band,"green_band": green_band,"blue_band": blue_band  
    }, function(data){
        alert( "Data Loaded: " + data["status"] );
        console.log(data["urls"]);
        RGB_tileUrls = data["urls"];
        runRGB_FalseColor_WebGL();
        map.setView(data["lat_lng"], data["maxZoom"]);
    });
    console.log('RBG False color got updated');    
});

/*
Action when person clicks on Single band Visualization button
*/
$("#single_band_visual").click(function() {
    console.log("Single Band Button was clicked");

    var image_selected = $( "#image_select_raster option:checked" ).val();
    var single_band_comma_sep = $('#comma_sep_band_nums').val();

    console.log(image_selected);
    console.log(single_band_comma_sep);

    updateRaster(map, image_name = image_selected, comma_sep_bands = single_band_comma_sep);
    console.log("Map got updated");

});



/*
Code for small shape file visualization using frontend
*/

var shapefile, m ;
    
function handleFileSelect(evt) {
    var files = evt.target.files; // FileList object
    console.log(files);
    var selFile = files[0];
    handleFile(selFile);
}

function handleFile(file){
var reader = new FileReader();
    reader.onload = function(e) {

        shapefile = new L.Shapefile(e.target.result,{isArrayBufer:true});
        shapefile.on("data:loaded", function (e){
            map.fitBounds(shapefile.getBounds());
        });
        shapefile.addTo(map);
    };

    reader.onerror = function(e) {
        console.log(e);
    };
    reader.readAsArrayBuffer(file);

}

document.getElementById('file').addEventListener('change', handleFileSelect, false);
function init(){
    
    var dropbox = document.getElementById("map");
    dropbox.addEventListener("dragenter", dragenter, false);
    dropbox.addEventListener("dragover", dragover, false);
    dropbox.addEventListener("drop", drop, false);
    dropbox.addEventListener("dragleave", function() {
        map.scrollWheelZoom.enable();
    }, false);

    function dragenter(e) {
        e.stopPropagation();
        e.preventDefault();
        map.scrollWheelZoom.disable();
    }

    function dragover(e) {
        e.stopPropagation();
        e.preventDefault();
    }

    function drop(e) {
        e.stopPropagation();
        e.preventDefault();
        map.scrollWheelZoom.enable();
        var dt = e.dataTransfer;
        var files = dt.files;

        var i = 0;
        var len = files.length;
        if (!len) {
            return
        }
        while (i < len) {
            handleFile(files[i]);
            i++;
        }
    }
}

init();

/*
Code for small shape file visualization using frontend ends here
*/

/*
Code for Vector Tile Visulization
*/

var vector_tile;

function VectorTileShow(data){
    console.log(data);
    vector_tile = L.vectorGrid.protobuf( data["path"], {
                maxNativeZoom: data["maxZoom"],
            });
    console.log(vector_tile);
    vector_tile.addTo(map);
    map.setView(data["lat_lng"], data["maxZoom"]);
}


$("#vector_image_show").click(function() {
    console.log("Vector Image Button was clicked");

    var image_selected = $( "#image_select_vector option:checked" ).val();
    console.log(image_selected);

    $.ajax({
        url: "/webclient/getVectorInfo",
        data: { "image_name": image_selected,},
        type: "GET",
        dataType: "json",
        success: function(response) {
            if (response["status"] == "success"){
                console.log(response);
                VectorTileShow(response["message"]);
            }
        },
        error: function(xhr, errmsg, err) {
            alert(xhr.status + ": " + xhr.responseText);
        }
    });

    console.log("Map with Vector Tile got updated");

});


/*
To create dynamically the dropdown in modals (Raster and Vector Tiles)
*/

function createDropdown(target, data){

    var input = document.getElementById(target);
    for (var i = 0; i < data.length; i++) {
        var element = document.createElement("option");
        element.innerText = data[i]["name"]; 
        element.setAttribute("value", data[i]["value"]);
        input.appendChild(element);

    }

}

function loadModalRaster(){

    $.ajax({
        url: "/webclient/getAllRasterBands",
        type: "GET",
        dataType: "json",
        success: function(response) {
            if (response["status"] == "success"){
                createDropdown("image_select_raster", response["message"]);
            }
        },
        error: function(xhr, errmsg, err) {
            alert(xhr.status + ": " + xhr.responseText);
        }
    });
}
loadModalRaster();

function loadModalVector(){

    $.ajax({
        url: "/webclient/getAllVectors",
        type: "GET",
        dataType: "json",
        success: function(response) {
            if (response["status"] == "success"){
                console.log(response);
                createDropdown("image_select_vector", response["message"]);
            }
        },
        error: function(xhr, errmsg, err) {
            alert(xhr.status + ": " + xhr.responseText);
        }
    });
}
loadModalVector();

/*
To create dynamically the dropdown in modals (Raster and Vector Tiles) ---- ends here
*/