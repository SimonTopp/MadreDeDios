
///////////////////Import Records Code
//First bring in all the collections and geometries we need.  After bringing the code into Earth Enginge, select 'convert' on this
//top chunk to change it into the import records.
var jrcYearly = ee.ImageCollection("JRC/GSW1_1/YearlyHistory"),
    hydrobasins = ee.FeatureCollection("WWF/HydroSHEDS/v1/Basins/hybas_8"),
    basinCenters = /* color: #d63000 */ee.Geometry.MultiPoint(
        [[-69.4777016746201, -12.576473368223164],
         [-69.87183619610448, -12.631421446135665],
         [-70.25910426251073, -12.652861398316732],
         [-69.91440821758886, -12.805568760913916],
         [-70.84525610775881, -12.50731774494869],
         [-71.10480810971194, -12.294058856099383],
         [-70.47584082455569, -12.232328903390181],
         [-70.75873877377444, -13.006908920479578],
         [-71.31492163510256, -12.75388811941324],
         [-76.74048426225272, 5.37644871980125],
         [113.90891462598738, -1.3240185713752917],
         [-2.0320518771662655, 6.175984402744373],
         [-61.52105563181567, 6.197007262413514],
         [-59.128905913782, 5.306470370318634]]),
    dummy =
    /* color: #d63000 */
    /* shown: false */
    ee.Geometry.Point([-70.39549711889492, -12.57195515697498]),
    hansen = ee.Image("UMD/hansen/global_forest_change_2018_v1_6"),
    Colombia = /* color: #d63000 */ee.Geometry.Point([-76.74032935359958, 5.376874612092712]),
    Ghana = /* color: #98ff00 */ee.Geometry.Point([-2.029830446820453, 6.161487617491079]),
    Indonesia =
    /* color: #0b4a8b */
    /* shown: false */
    ee.Geometry.Point([113.90879537955092, -1.3240711724748622]),
    Guyana =
    /* color: #d63000 */
    /* shown: false */
    ee.Geometry.Point([-59.12119873060829, 5.324561169879806]),
    Global =
    /* color: #98ff00 */
    /* shown: false */
    ee.Geometry.MultiPoint(
        [[113.9093916639091, -1.324760688066352],
         [-2.02892744293099, 6.176407869454533],
         [-61.57110205995499, 6.357064138067821],
         [-76.73961758973644, 5.37707491160719],
         [-59.11547510852289, 5.318167012556783]]),
    Venezuela =
    /* color: #0b4a8b */
    /* shown: false */
    ee.Geometry.Point([-61.52828266780531, 6.216810578040001]),
    StudyArea =
    /* color: #ffc82d */
    /* shown: false */
    /* displayProperties: [
      {
        "type": "rectangle"
      }
    ] */
    ee.Geometry.Polygon(
        [[[-71.39402033107247, -11.877185960908811],
          [-71.39402033107247, -13.185556498434742],
          [-69.19675470607247, -13.185556498434742],
          [-69.19675470607247, -11.877185960908811]]], null, false);


//////////////////Analysis Code
//// River area calculations adapted from Xio Yang's RivWidthCloud
/// Yang et al. 2020 IEEE Geoscience

// Modified function for calculating channel masks and centerline lengths

//Set up an assign default function
var AssignDefault = function(x, dv) {
  return(typeof x !== 'undefined' ? x : dv);
};

//Set up the function to extract the channel mask see
//See 'users/eeProject/RivWidthCloudPaper' for function details

exports.rwGenSR_waterMask = function(MAXDISTANCE, FILL_SIZE, MAXDISTANCE_BRANCH_REMOVAL, AOI) {

  // assign default values
  MAXDISTANCE = AssignDefault(MAXDISTANCE, 4000);
  FILL_SIZE = AssignDefault(FILL_SIZE, 333);
  MAXDISTANCE_BRANCH_REMOVAL = AssignDefault(MAXDISTANCE_BRANCH_REMOVAL, 500);
  AOI = AssignDefault(AOI, null);

  var grwl = ee.FeatureCollection("users/eeProject/grwl");//.filter(ee.Filter.gt('width_m', 90))
  var riverFun = require('users/eeProject/RivWidthCloudPaper:functions_river.js');
  var clWidthFun = require('users/eeProject/RivWidthCloudPaper:functions_centerline_width.js');

  // generate function based on user choice
  var tempFUN = function(img) {

    // Calculate river mask
    var imgOut = riverFun.ExtractRiver(img, grwl, MAXDISTANCE, FILL_SIZE);

    // Calculate centerline
    imgOut = clWidthFun.CalculateCenterline(imgOut);

    return(imgOut);
  };

  return(tempFUN);
};

//Bring in some initial feature collections

// Level 8 hydroBasins filtered to study watersheds
var hb = hydrobasins.filterBounds(basinCenters);

// GRWL River Centerlines
var grwl = ee.FeatureCollection("users/eeProject/grwl")
  .filterBounds(hb);

//Set up the visualizations
Map.centerObject(dummy, 12);
Map.setOptions("hybrid");


//////Centerline and Hydroscape Areas//////////////////////////////
//////Centerline and Hydroscape Areas//////////////////////////////
//////Centerline and Hydroscape Areas//////////////////////////////
//////Centerline and Hydroscape Areas//////////////////////////////

// Initiate and apply the RivWidthCloud Function

//1500 maxDist for Peru, 100 for global Rivs.  This is because global rivs are
//much smaller and have migrated significantly less over the study period. Using
//a smaller maxDist reduces misclassifications of lentic/lotic surface extent in these
//cases
var rwc = exports.rwGenSR_waterMask(100, 1000, 500);
//Map function over years to generate hydroscape image collection. We use Pekel annual
//and seasonal watermask for the input.

var yearChange = function(y){

  //Unfortunately Pekel has lots of gaps so we'll use 2 year composite watermasks and also dilate/erode our image
  //to fill small holes in the river since we need continuity.
  //We'll use an undilated mask for the non river area.

  //Make Dilated mask for the river
  var maskDL = ee.Image(jrcYearly.filter(ee.Filter.calendarRange(ee.Number(y).subtract(1),y, 'year'))
  .reduce(ee.Reducer.max()))
  .gte(2).rename('waterMask')
  .unmask(0)
  .focal_max(2.5)
  .focal_min(2.5)
  .clip(hb.geometry());

  //Make an undilated mask for the rest of the area
  var mask = ee.Image(jrcYearly.filter(ee.Filter.calendarRange(ee.Number(y).subtract(1),y, 'year'))
  .reduce(ee.Reducer.max()))
  .gte(2).rename('waterMask')
  .unmask(0)
  .clip(hb.geometry());

  var hydroscape = rwc(mask.set('scale',30).set('image_id', y).unmask(0));
  var hydroscapeDL = rwc(maskDL.set('scale',30).set('image_id', y).unmask(0));

  //Combine the dilated river with the undilated landscape for out
  //final surface water mask
  var water = hydroscape.select('waterMask').eq(1)
  .or(hydroscapeDL.select('channelMask').eq(1)).rename('waterMask');
  //Overwrite the dilated watermask for the output
return hydroscapeDL.addBands(water, ['waterMask'], true).set('year', y);
};

var years = ee.List.sequence(1985,2018,1);

var hydroscape = ee.ImageCollection(years.map(yearChange));

//Some quality control, check the watermask/channel mask/centerline for a given year.
var imgCheck= ee.Image(hydroscape.filter(ee.Filter.eq('year', 2017)).first());

//EPSG":32719  UTM Z19S
//Reproject the cl for visualization.
//var cl = imgCheck.select('cleanedCL').eq(1).selfMask().reproject('EPSG:4326', null, 30)
//var clRaw = imgCheck.select('rawCL').eq(1).selfMask().reproject('EPSG:4326', null, 30)

//Visualize change over time by stacking up the layers on top of each other
var watermasks = hydroscape.map(function(i){
  var mask = i.select('waterMask').eq(1).selfMask();
  var year = ee.Image(ee.Number(i.get('year'))).updateMask(mask).toFloat();
  return year;
});

var waterStack = watermasks.reduce(ee.Reducer.min());

///Now make a function to calculate basin scale areas on yearly basis and export
// them to drive

var areasOut = function(year){
  var hydro = ee.Image(hydroscape.filter(ee.Filter.eq('year', year)).first());
  var clLength = hydro.select('cleanedCL').eq(1).selfMask()
  .reduceRegions(hb, ee.Reducer.sum(), 30)
  .select(['HYBAS_ID','sum'], ['BasinID','area'], false)
  .map(function(i){return i.set('feature', 'cl').set('year', year)});

  var channelMask = hydro.select('channelMask').eq(1).selfMask();
  var waterMask = hydro.select('waterMask').eq(1).selfMask();

  var rivArea = ee.Image.pixelArea().updateMask(channelMask)
    .reduceRegions(hb, ee.Reducer.sum(), 30)
    .select(['HYBAS_ID','sum'], ['BasinID','area'], false)
    .map(function(i){return i.set('feature', 'rivArea').set('year', year)});

  var waterArea = ee.Image.pixelArea().updateMask(waterMask)
    .reduceRegions(hb, ee.Reducer.sum(), 30)
    .select(['HYBAS_ID','sum'], ['BasinID','area'], false)
    .map(function(i){return i.set('feature', 'waterArea').set('year', year)});

  var featsOut = clLength.merge(rivArea).merge(waterArea);
return featsOut;
};

var hydro_ts = ee.FeatureCollection(years.map(areasOut));

//////////////////////////////
////////Quick look at forest cover
///////////////////////////////

//Add 2000 to the hansen values so each value corresponds with a year
var fl = hansen.select('lossyear').selfMask().clip(hb).add(2000);

var flyear = function(year){
  var loss = fl.eq(ee.Number(year)).set('year', year);
  return loss;
};

//Generate annual images for forest loss
var yearlyLoss = ee.ImageCollection(ee.List.sequence(2001, 2018, 1).map(flyear));

//To control for forest loss due to river migration mask out the channel
//for the entire timespan.

var rivMaskFull = hydroscape.map(function(i){
  return i.select('channelMask').eq(1);
}).reduce(ee.Reducer.max());

fl = fl.updateMask(rivMaskFull.not());

// Set up function to calculate annual deforestation by basin by year
var forestAreasCalcs = function(year){
  var loss = fl.eq(ee.Number(year)).selfMask().set('year', year);
  var water = hydroscape.filter(ee.Filter.eq('year', ee.Number(year).add(1).min(2018))).first()
    .select('waterMask').eq(1);
  var areaWater = ee.Image.pixelArea().updateMask(loss).updateMask(water)
    .reduceRegions(hb, ee.Reducer.sum(), 30)
    .select(['HYBAS_ID','sum'], ['BasinID','area'], false)
    .map(function(i){return i.set('feature', 'ForestToWater').set('year', year)});
  var areaBarren = ee.Image.pixelArea().updateMask(loss).updateMask(water.not())
    .reduceRegions(hb, ee.Reducer.sum(), 30)
    .select(['HYBAS_ID','sum'], ['BasinID','area'], false)
    .map(function(i){return i.set('feature', 'ForestToBarren').set('year', year)});
  return areaWater.merge(areaBarren);
};

var forestAreas = ee.FeatureCollection(ee.List.sequence(2001, 2018, 1)
  .map(forestAreasCalcs)).flatten();

//////////////////////////////
////////Visualize/export/print
///////////////////////////////

//Map.addLayer(fl, {min: 2001, max: 2018, palette:["#440154FF", "#3B528BFF", "#21908CFF", "#5DC863FF", "#FDE725FF"]}, 'forestLoss')
//Map.addLayer(imgCheck.select('waterMask').eq(1).selfMask(), {palette: 'cyan'}, 'WaterMask');
Map.addLayer(ee.Image(waterStack), {min: 1984, max: 2018, palette:["#440154FF", "#3B528BFF", "#21908CFF", "#5DC863FF", "#FDE725FF"]}, 'stack')
Map.addLayer(hb, {color:'grey'}, 'hb')
//Map.addLayer(clRaw, {palette: 'green'}, 'clRaw')
Map.addLayer(grwl, {color: 'green'}, 'grwl')
Map.addLayer(imgCheck.select('channelMask').eq(1).selfMask(), {palette:'magenta'}, 'channel')
//Map.addLayer(cl, {palette: 'blue'}, 'cl')

print(hydroscape)
//print(hydro_ts.flatten(), 'hydro_ts')


Export.table.toDrive({collection: hydro_ts.flatten(),
                      description: 'MdD_Hydroscape',
                      folder: 'MdD_Exports'})


Export.table.toDrive({collection: forestAreas,
                      description: 'MdD_BasinDeforestation',
                      folder: 'MdD_Exports'})

Export.image.toDrive({image:waterStack,
                      description:'PeruStack_200',
                      folder: 'MdD_Exports',
                      region: hb.filterBounds(StudyArea),
                      scale: 200
})



//Put together a quick UI for visual quality control checks
var showLayer = function(year) {
  Map.layers().reset();
  var image = ee.Image(hydroscape.filter(ee.Filter.eq('year', year)).first())
  var water = image.select('waterMask').eq(1).selfMask()
  var channel = image.select('channelMask').eq(1).selfMask()
  Map.addLayer(water, {palette: 'cyan'}, 'water');
  Map.addLayer(channel, {palette: 'magenta'}, 'water');
  Map.addLayer(grwl, {color:'red'}, 'grwl')
};

// Create a label and slider.
var label = ui.Label('Yearly Water Masks');
var slider = ui.Slider({
  min: 1985,
  max: 2018,
  step: 1,
  onChange: showLayer,
  style: {stretch: 'horizontal'}
});

// Create a panel that contains both the slider and the label.
var panel = ui.Panel({
  widgets: [label, slider],
  layout: ui.Panel.Layout.flow('vertical'),
  style: {
    position: 'top-center',
    padding: '7px'
  }
});

// Add the panel to the map.
Map.add(panel);
