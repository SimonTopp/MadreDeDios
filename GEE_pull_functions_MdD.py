#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Google Earth Engine Reflectance Pull Functions
Created on Mon Apr  9 14:24:13 2018
@author: simontopp
"""

# Add filler panchromatic band to landsat 5 images.

###These are functions for unpacking the bit quality assessment band for TOA  
def Unpack(bitBand, startingBit, bitWidth):
  #unpacking bit bands
  #see: https://groups.google.com/forum/#!starred/google-earth-engine-developers/iSV4LwzIW7A
  return (ee.Image(bitBand)\
  .rightShift(startingBit)\
  .bitwiseAnd(ee.Number(2).pow(ee.Number(bitWidth)).subtract(ee.Number(1)).int()))
  
def UnpackAll(bitBand, bitInfo):
  unpackedImage = ee.Image.cat([Unpack(bitBand, bitInfo[key][0], bitInfo[key][1]).rename([key]) for key in bitInfo])
  return unpackedImage

def clipImage(image):
  return image.clip(lake.geometry())

def masking(image):
  if collection == 'SR':
    bitAffected = {
    'Water': [2,1],
    'Cloud': [5, 1],
    'CloudShadow': [3, 1],
    'CirrusConfidence': [8,2], 
    'SnowIceConfidence': [4, 1]  #Realized that sometimes super turbid waterbodies are
    #flagged as snow/ice, subsequently you can't filter by this unless you know your area
    #is unaffected by commission errors.
    }
  
  else:
    bitAffected = {
    'Cloud': [4, 1],
    'CloudShadow': [7, 2],
    'CirrusConfidence': [11,2]
    #'SnowIceConfidence': [9, 2]
    }
  

  ## Create layer to mask out roads that might not show up in Pekel and potentially 
  #corrupt pixel values  
  road = ee.FeatureCollection("TIGER/2016/Roads").filterBounds(lake.geometry()).geometry().buffer(30) 
  
  #Select qa band
  qa = image.select('qa')
  
  qaUnpack = UnpackAll(qa, bitAffected)
  
  fWater = qaUnpack.select('Water').eq(1)
  #pWater = water.clip(lake.geometry())
  

  if collection == 'SR':
    cScore = qaUnpack.select('Cloud').eq(1)\
    .Or(qaUnpack.select('CloudShadow').eq(1))\
    .Or(qaUnpack.select('CirrusConfidence').eq(3))\
    .Or(qaUnpack.select('SnowIceConfidence').eq(1))\
    .paint(road,1)#.Not()
  # else:
  #   mask = qaUnpack.select('Cloud').eq(1)\
  #   .Or(qaUnpack.select('CloudShadow').eq(3))\
  #   .Or(qaUnpack.select('CirrusConfidence').eq(3))\
  #   .paint(road,1).Not()
  # 
  #Create water only mask

  cScore = cScore.reduceRegion(ee.Reducer.sum(),lake.geometry(), 30).get('Cloud')
    
  #Update mask on imagery and add Pekel occurrence band for data export.
  masked = image.addBands(pekel.select('occurrence'))\
  .updateMask(fWater).set({'cScore':cScore})
  
  return masked


## These functions all go into calculating the USGS Dynamic water m

def AddFmaskSR(image):
   bitInfo = {
       'Cloud': [4, 1],
       # 'CloudConfidence': [5, 2],
       'CloudShadowConfidence': [7, 2],
       'SnowIceConfidence': [9, 2]
   }
   temp = UnpackAll(image.select(['qa']), bitInfo)

   ## define fmask water manually
   ndvi = image.normalizedDifference(['Nir', 'Red'])
   nir = image.select(['Nir'])
   fwater = ndvi.lt(0.01).And(nir.lt(0.11)).Or(ndvi.lt(0.1).And(nir.lt(0.05)))

   fmask = (fwater.rename(['fmask'])
   .where(temp.select(['SnowIceConfidence']).eq(3), ee.Image(3))
   .where(temp.select(['CloudShadowConfidence']).eq(3), ee.Image(2))
   .where(temp.select(['Cloud']), ee.Image(4))
   ).mask(temp.select(['Cloud']).gte(0)) ## mask the fmask so that it has the same footprint as the qa band

   return image.addBands(fmask)

def Mndwi(image):
  return image.normalizedDifference(['Green', 'Swir1']).rename('mndwi')
  
def Mbsrv(image):
  return image.select(['Green']).add(image.select(['Red'])).rename('mbsrv')
  
def Mbsrn(image):
  return image.select(['Nir']).add(image.select(['Swir1'])).rename('mbsrn')

def Ndvi(image):
  return image.normalizedDifference(['Nir', 'Red']).rename('ndvi')

def Awesh(image):
  return (image.addBands(Mbsrn(image))
  .expression('Blue + 2.5 * Green + (-1.5) * mbsrn + (-0.25) * Swir2', {
    'Blue': image.select(['Blue']),
    'Green': image.select(['Green']),
    'mbsrn': Mbsrn(image).select(['mbsrn']),
    'Swir2': image.select(['Swir2'])
    }))


## The DSWE Function itself    
def Dswe(i):
  mndwi = Mndwi(i)
  mbsrv = Mbsrv(i)
  mbsrn = Mbsrn(i)
  awesh = Awesh(i)
  swir1 = i.select(['Swir1'])
  nir = i.select(['Nir'])
  ndvi = Ndvi(i)
  blue = i.select(['Blue'])
  swir2 = i.select(['Swir2'])

  t1 = mndwi.gt(0.124)
  t2 = mbsrv.gt(mbsrn)
  t3 = awesh.gt(0)
  t4 = (mndwi.gt(-0.44)
  .And(swir1.lt(900))
  .And(nir.lt(1500))
  .And(ndvi.lt(0.7)))
  t5 = (mndwi.gt(-0.5)
  .And(blue.lt(1000))
  .And(swir1.lt(3000))
  .And(swir2.lt(1000))
  .And(nir.lt(2500)))
  
  t = t1.add(t2.multiply(10)).add(t3.multiply(100)).add(t4.multiply(1000)).add(t5.multiply(10000))
  
  noWater = (t.eq(0)
  .Or(t.eq(1))
  .Or(t.eq(10))
  .Or(t.eq(100))
  .Or(t.eq(1000)))
  hWater = (t.eq(1111)
  .Or(t.eq(10111))
  .Or(t.eq(11011))
  .Or(t.eq(11101))
  .Or(t.eq(11110))
  .Or(t.eq(11111)))
  mWater = (t.eq(111)
  .Or(t.eq(1011))
  .Or(t.eq(1101))
  .Or(t.eq(1110))
  .Or(t.eq(10011))
  .Or(t.eq(10101))
  .Or(t.eq(10110))
  .Or(t.eq(11001))
  .Or(t.eq(11010))
  .Or(t.eq(11100)))
  pWetland = t.eq(11000)
  lWater = (t.eq(11)
  .Or(t.eq(101))
  .Or(t.eq(110))
  .Or(t.eq(1001))
  .Or(t.eq(1010))
  .Or(t.eq(1100))
  .Or(t.eq(10000))
  .Or(t.eq(10001))
  .Or(t.eq(10010))
  .Or(t.eq(10100)))
  
  iDswe = (noWater.multiply(0)
  .add(hWater.multiply(1))
  .add(mWater.multiply(2))
  .add(pWetland.multiply(3))
  .add(lWater.multiply(4)))
  
  return iDswe.rename('dswe')


## Calculuate hillshades to correct DWSE
def CalcHillShades(image, geo):
  MergedDEM = ee.Image("users/eeProject/mergedSrtmHAE").clip(geo)
  
  ### The shift distance code is just for taking a mean to get rid of striping in high latitudes.  Not used here.
  
  #  shiftDistance = 30
  #  dp1 = ee.Image.cat(ee.Image(shiftDistance), ee.Image(shiftDistance))
  #  dp2 = ee.Image.cat(ee.Image(-shiftDistance), ee.Image(shiftDistance))
  #  dp3 = ee.Image.cat(ee.Image(shiftDistance), ee.Image(-shiftDistance))
  #  dp4 = ee.Image.cat(ee.Image(-shiftDistance), ee.Image(-shiftDistance))
  # 
  #  hillShade1 = (ee.Terrain.hillshade(mergedDEM.displace(dp1),
  # ee.Number(image.get('SOLAR_AZIMUTH_ANGLE')).add(360),
  # image.get('SOLAR_ZENITH_ANGLE')).rename(['hillShade']))
  # 
  #  hillShade2 = (ee.Terrain.hillshade(mergedDEM.displace(dp2),
  # ee.Number(image.get('SOLAR_AZIMUTH_ANGLE')).add(360),
  # image.get('SOLAR_ZENITH_ANGLE')).rename(['hillShade']))
  # 
  #  hillShade3 = (ee.Terrain.hillshade(mergedDEM.displace(dp3),
  # ee.Number(image.get('SOLAR_AZIMUTH_ANGLE')).add(360),
  # image.get('SOLAR_ZENITH_ANGLE')).rename(['hillShade']))
  # 
  #  hillShade4 = (ee.Terrain.hillshade(mergedDEM.displace(dp4),
  # ee.Number(image.get('SOLAR_AZIMUTH_ANGLE')).add(360),
  # image.get('SOLAR_ZENITH_ANGLE')).rename(['hillShade']))
  # 
  # // # // ee.Algorithms.HillShadow
  #  hillShade = ee.ImageCollection.fromImages([hillShade1, hillShade2, hillShade3, hillShade4]).mean()
  
  hillShade = (ee.Terrain.hillshade(MergedDEM, ee.Number(image.get('SOLAR_AZIMUTH_ANGLE')).add(360),
  image.get('SOLAR_ZENITH_ANGLE')).rename(['hillShade']))
  return hillShade
  
def lakePull(image):
  
  if PekelMask == True:
    waterOut = masking(image)
    
  if PekelMask == False:
    def waterOnly(image):
      f = AddFmaskSR(image).select('fmask')
      cScore = f.eq(2).Or(f.eq(3)).Or(f.eq(4))
      cScore = cScore.reduceRegion(ee.Reducer.sum(),lake.geometry().buffer(100), 30).get('fmask')
      d = Dswe(image).select('dswe')
      h = CalcHillShades(image, lake.geometry()).select('hillShade')
      water = image.updateMask(f.lt(2)).updateMask(d.eq(1))
      waterCount = water.reduceRegion(ee.Reducer.count(), lake.geometry().buffer(100), 30).get('Blue')
      return (image.clip(lake.geometry().buffer(100))
      .addBands(f).addBands(d).addBands(h)
      .updateMask(f.lt(2)).updateMask(d.eq(1).Or(d.eq(2)))
      .set({'cScore':cScore}).set({'waterCount':waterCount}))

    
    waterOut = waterOnly(image)

  #Collect median reflectance and occurance values
  lsout = waterOut.reduceRegion(ee.Reducer.median(), lake.geometry().buffer(100), 30)
  
  #Collect reflectance and occurence st.dev.
  lsdev = waterOut.reduceRegion(ee.Reducer.stdDev(), lake.geometry().buffer(100), 30)
  
  #Pull Sat info
  if collection == 'SR':
    mission = ee.String(image.get('SATELLITE')).split('_').get(1)
  else:
    mission = ee.String(image.get('SPACECRAFT_ID')).split('_').get(1)
    
  #Create dictionaries of median values and attach them to original site feature.
    
  output = shell.set({"blue": lsout.get('Blue')})\
  .set({'Oxbow_ID':lake.get('Name')})\
  .set({'sat': mission})\
  .set({'date': ee.Date(image.get('system:time_start'))})\
  .set({"blue": lsout.get('Blue')})\
  .set({"green": lsout.get('Green')})\
  .set({"red": lsout.get('Red')})\
  .set({"nir": lsout.get('Nir')})\
  .set({"swir1": lsout.get('Swir1')})\
  .set({"swir2": lsout.get('Swir2')})\
  .set({"qa": lsout.get('qa')})\
  .set({"swir1_sd": lsdev.get('Swir1')})\
  .set({"waterCount": waterOut.get('waterCount')})\
  .set({'path': image.get('WRS_PATH')})\
  .set({'row': image.get('WRS_ROW')})\
  .set({'cScore': waterOut.get('cScore')})\
  .set({'Cloud_Cover': image.get('CLOUD_COVER')})\
  .set({'dswe': lsout.get('dswe')})\
  .set({'dswe_sd':lsdev.get('dswe')})\
  .set({'hillshade':lsout.get('hillShade')})\
  .set({'azimuth': image.get('SOLAR_AZIMUTH_ANGLE')})\
  .set({'zenith': image.get('SOLAR_ZENITH_ANGLE')})\
  .set({'OrderUp': lake.get('Order_Up')})
  
  return output
  
  
def lakeVar(image):
  
  if PekelMask == True:
    waterOut = masking(image)
    
  if PekelMask == False:
    def waterOnly(image):
      date = ee.Image.constant(image.get('system:time_start')).rename('date')
      f = AddFmaskSR(image).select('fmask')
      cScore = f.eq(2).Or(f.eq(3)).Or(f.eq(4))
      cScore = cScore.reduceRegion(ee.Reducer.sum(),lake.geometry(), 30).get('fmask')
      d = Dswe(image).select('dswe')
      h = CalcHillShades(image, lake.geometry()).select('hillShade')
      return image.addBands(date).addBands(f).addBands(d).addBands(h).updateMask(f.lt(2))\
      .updateMask(d.eq(1)).set({'cScore':cScore})
    
    waterOut = waterOnly(image)

  #Collect median reflectance and occurance values
  lsVar = (waterOut.sample(region = lake.geometry(), 
  scale = 30, projection = waterOut.select('Blue').projection(), 
  numPixels = 500, dropNulls = False))
  
  return lsVar  

##Function for limiting the max number of tasks sent to
#earth engine at one time to avoid time out errors

def maximum_no_of_tasks(MaxNActive, waitingPeriod):
  ##maintain a maximum number of active tasks
  time.sleep(10)
  ## initialize submitting jobs
  ts = list(ee.batch.Task.list())

  NActive = 0
  for task in ts:
       if ('RUNNING' in str(task) or 'READY' in str(task)):
           NActive += 1
  ## wait if the number of current active tasks reach the maximum number
  ## defined in MaxNActive
  while (NActive >= MaxNActive):
      time.sleep(waitingPeriod) # if reach or over maximum no. of active tasks, wait for 2min and check again
      ts = list(ee.batch.Task.list())
      NActive = 0
      for task in ts:
        if ('RUNNING' in str(task) or 'READY' in str(task)):
          NActive += 1
  return()
    