"""This is a general purpose module containing routines
(a) that are used in multiple notebooks; or
(b) that are complicated and would thus otherwise clutter notebook design.
"""

import re
import socket
import numpy as np
from datetime import datetime
import intake
import xarray as xr
import cftime


def is_ncar_host():
    """Determine if host is an NCAR machine."""
    hostname = socket.getfqdn()

    return any([re.compile(ncar_host).search(hostname)
                for ncar_host in ['cheyenne', 'casper', 'hobart']])


def simple_spatial_average(dsvar, lat_bounds=[-90, 90], lon_bounds=[0, 360]):
    '''
    simple_spatial_average(dsvar)

    weighted average for DataArrays

    Function does not yet handle masked data.

    Parameters
    ----------
    dsvar : data array variable (with lat / lon axes)

    Optional Arguments
    ----------
    lat_bounds : list of latitude bounds to average over (e.g., [-20., 20.])
    lon_bounds : list of longitude bounds to average over (e.g., [0., 360.])

    Returns
    -------
    NewArray : DataArray
        New DataArray with proper spatial weighting.

    '''
    # Make sure lat and lon ranges are in correct order
    if lat_bounds[0] > lat_bounds[1]:
        lat_bounds = np.flipud(lat_bounds)
    if lon_bounds[0] > lon_bounds[1]:
        lon_bounds = np.flipud(lon_bounds)
    if float(dsvar.lon.min().values) < 0.:
        raise ValueError('Not expecting longitude values less than 0.')
    # Subset data into a box
    dsvar_subset = dsvar.sel(lat=slice(lat_bounds[0], lat_bounds[1]),
                             lon=slice(lon_bounds[0], lon_bounds[1]))
    # Get weights (cosine(latitude))
    w = np.cos(np.deg2rad(dsvar_subset.lat))
    # Ensure weights are the same shape as the data array
    w = w.broadcast_like(dsvar_subset)
    # Convolve weights with data array
    x = (dsvar_subset*w).mean(dim=['lat', 'lon']) / w.mean(dim=['lat', 'lon'])

    return x


def get_anomaly(dsvar):
    '''
    get_anomaly(dsvar)

    remove climatological annual cycle to compute anomalies


    Parameters
    ----------
    dsvar : data array variable


    Returns
    -------
    NewArray : DataArray
        New DataArray with seasonal cycle removed.

    '''
    climatology = dsvar.groupby('time.month').mean('time')
    anomalies = dsvar.groupby('time.month') - climatology
    return anomalies


def get_decimal_time(dsvar):
    '''
    get_decimal_time(dsvar)

    get the time in decimal units (e.g., 1979.0438...)


    Parameters
    ----------
    dsvar : data array variable


    Returns
    -------
    dtime : ndarray
        Array of time axis in decimal units

    '''
    dtime = []
    for t in dsvar.time:
        # differentiate between datetime64 and datetime objects
        if isinstance(t.item(), int):
            t = datetime.utcfromtimestamp(t.item()/1e9)
        else:
            t = t.item()
        doy = t.timetuple().tm_yday
        dtime.append(t.year + doy / 365.)
    dtime = np.array(dtime)
    return dtime


def upscale(x,y,field,f):
    'Reduces resolution of field by factor f'
    
    xdel=(x[1]-x[0])/2
    xbin=np.zeros(int(len(x)/2)+1)
    xbin[0:-1]=x[::f].values-xdel.values
    xbin[-1]=x[-1].values+xdel.values
    
    ydel=(y[1]-y[0])/2
    ybin=np.zeros(int(len(y)/2)+1)
    ybin[0:-1]=y[::f].values-ydel.values
    ybin[-1]=y[-1].values+ydel.values
    
    xn=x.groupby_bins(group=x.name,bins=xbin).mean(x.name)
    yn=y.groupby_bins(group=y.name,bins=ybin).mean(y.name)
    fieldn=field.groupby_bins(group=x.name,bins=xbin).mean(x.name,skipna=True)\
        .groupby_bins(group=y.name,bins=ybin).mean(y.name,skipna=True)
    fieldn=fieldn.rename({'lat_bins':'lat','lon_bins':'lon'})
    fieldn[x.name].values=xn
    fieldn[y.name].values=yn
    
    return fieldn

def reindex_time(startingtimes):
    newtimes = startingtimes.values
    for i in range(0,len(startingtimes)):
        yr = int(str(startingtimes.values[i])[0:4])
        mon = int(str(startingtimes.values[i])[5:7])
        day = int(str(startingtimes.values[i])[8:10])
        hr = int(str(startingtimes.values[i])[11:13])
        newdate = cftime.DatetimeProlepticGregorian(yr,mon,15)
        newtimes[i]=newdate
    return newtimes
