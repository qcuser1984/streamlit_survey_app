#standard library imports
import os
import io
import random
from math import sqrt, dist
from datetime import datetime, timedelta
from functools import wraps 
#fancy modules imports
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
from scipy.spatial import distance

import warnings
warnings.filterwarnings('ignore')

fourD_nav = r"Q:\06-ARAM\nav\Postplot_R\4dnav_lines\BR001522_4dnav.csv"
fourD_nav_r = r"Q:\ITAPU\nav\Postplot_R\4dnav_lines\MT1001021_4dnav.csv"
all_clean_s = r"Q:\ARAM\nav\Postplot_S\All_Seq_Clean.s01"


sps_s_preplot = r"Q:\ARAM\nav\preplot.s01"
sequence_stats = r"C:\scripts\anne\extras\st_survey_app\sequence_stats.txt"

def exc_time(func):
    '''print out function execution time'''
    @wraps(func)
    def wrapper(*args,**kwargs):
        start=datetime.utcnow()
        smth=func(*args,**kwargs)
        stop=datetime.utcnow()
        print(f'{func.__name__} executed in {round((stop-start).total_seconds(),3)} seconds')
        return(smth)
    return(wrapper)


def sps_to_frame_skip(path_to_sps,char):
    '''get a number of rows to skip to account for header'''
    try:
        with open(path_to_sps, 'r',encoding='utf-8') as file:
            lines = file.readlines()
            first_data_line=[i for i in lines if i.startswith(char)][0]
            to_skip=int(lines.index(first_data_line))
            return(to_skip)
    except Exception as exc:
        print(f'Something went wrong: {exc}')
        return None


def add_error(number, error=11):
    ''' add some deviation in percents to a value '''
    return round(number * (random.randint(-error, error)/100+1))

#get only the deployment related columns from 4dnav
def read_4dnav_for_receivers(file_path):
    if os.path.exists(file_path) and os.stat(file_path).st_size != 0:
        try:
            nav_df=pd.read_csv(file_path, skiprows=8)
            nav_df['DeploymentDateTime'] = nav_df["Aslaid Time"].apply(lambda x: datetime.strptime(x, "%Y-%m-%d %H:%M:%S.%f"))
            nav_df['DeploymentDate'] = nav_df['DeploymentDateTime'].apply(lambda x: x.date())
            nav_df['JulianDay'] = nav_df['DeploymentDate'].apply(lambda x: int(datetime.strftime(x, "%j")))
            nav_df["DeploymentDateStr"] = nav_df['DeploymentDate'].apply(lambda x: datetime.strftime(x, "%Y-%m-%d"))
            nav_df["OnSeabed"] = (datetime.utcnow() - nav_df['DeploymentDateTime']).dt.days + 1
            nav_df.rename(columns={"Preplot Easting":"PreplotEasting","Preplot Northing":"PreplotNorthing","Preplot Depth":"PreplotDepth",
                       "Aslaid Easting":"AslaidEasting","Aslaid Northing":"AslaidNorthing","Aslaid Depth":"AslaidDepth",
                       "Aslaid Tide Offset":"AslaidTideOffset","Aslaid Azimuth":"AslaidAzimuth","Is Aslaid Adjusted":"IsAslaidAdjusted",
                       "Recovered Time":"RecoveryDateTime","Recovered Easting":"RecoveredEasting","Recovered Northing":"RecoveredNorthing",
                       "Recovered Depth":"RecoveredDepth", "Recovered Tide Offset":"RecoveredTideOffset","Recovered Azimuth":"RecoveredAzimuth",
                       "Is Recovered Adjusted":"IsRecoveredAdjusted","Deployed by ROV":"DeploymentROV","Recovered by ROV":"RecoveryROV"}, inplace=True)
            nav_df.drop(columns=["Aslaid Time","DeployedComments","RecoveredComments"], inplace=True)
            nav_df = nav_df[["Line","Point","NodeCode","Index","PreplotEasting","PreplotNorthing","PreplotDepth","AslaidEasting","AslaidNorthing","AslaidDepth","AslaidTideOffset","AslaidAzimuth",
                            'PreplotToAslaidDistance','PreplotToAslaidBearing',"PreplotToAslaidAlongTrack","PreplotToAslaidCrossTrack",'DeploymentROV','DeploymentDateTime','DeploymentDate','JulianDay',"OnSeabed","DeploymentDateStr"]]
            nav_df.fillna(0,inplace=True)
            return nav_df
        except Exception as exc:
            print(f"{exc}")
            return None
    else:
        return None


def read_4dnav_for_recovered(file_path):
    if os.path.exists(file_path) and os.stat(file_path).st_size != 0:
        try:
            nav_df=pd.read_csv(file_path, skiprows=8)
            nav_df['DeploymentDateTime'] = nav_df["Aslaid Time"].apply(lambda x: datetime.strptime(x, "%Y-%m-%d %H:%M:%S.%f"))
            nav_df['DeploymentDate'] = nav_df['DeploymentDateTime'].apply(lambda x: x.date())
            nav_df.rename(columns={"Preplot Easting":"PreplotEasting","Preplot Northing":"PreplotNorthing","Preplot Depth":"PreplotDepth",
                       "Aslaid Easting":"AslaidEasting","Aslaid Northing":"AslaidNorthing","Aslaid Depth":"AslaidDepth",
                       "Aslaid Tide Offset":"AslaidTideOffset","Aslaid Azimuth":"AslaidAzimuth","Is Aslaid Adjusted":"IsAslaidAdjusted",
                       "Recovered Time":"RecoveryDateTime","Recovered Easting":"RecoveredEasting","Recovered Northing":"RecoveredNorthing",
                       "Recovered Depth":"RecoveredDepth", "Recovered Tide Offset":"RecoveredTideOffset","Recovered Azimuth":"RecoveredAzimuth",
                       "Is Recovered Adjusted":"IsRecoveredAdjusted","Deployed by ROV":"DeploymentROV","Recovered by ROV":"RecoveryROV"}, inplace=True)
            nav_df.drop(columns=["Aslaid Time","DeployedComments","RecoveredComments"], inplace=True)
            #nav_df = nav_df.query('Line ! = 4819')
            nav_df = nav_df[nav_df["RecoveryDateTime"] == nav_df["RecoveryDateTime"]] # filter the unrecovered with the recovery time
            nav_df["RecoveryDateTime"] = nav_df["RecoveryDateTime"].apply(lambda x: datetime.strptime(x, "%Y-%m-%d %H:%M:%S.%f"))
            nav_df["RecoveryDate"] = nav_df["RecoveryDateTime"].apply(lambda x: x.date())
            nav_df['JulianDay'] = nav_df['RecoveryDate'].apply(lambda x: int(datetime.strftime(x, "%j")))
            nav_df["OnSeabed"] = (nav_df["RecoveryDate"] - nav_df["DeploymentDate"]).dt.days + 1
            nav_df['JulianDay'] = nav_df['RecoveryDate'].apply(lambda x: int(datetime.strftime(x, "%j")))
            nav_df = nav_df[["Line","Point","NodeCode","Index","PreplotEasting","PreplotNorthing", "RecoveryDateTime", "RecoveredEasting","RecoveredNorthing","RecoveredDepth","RecoveredTideOffset","RecoveredAzimuth","IsRecoveredAdjusted",
                            "AslaidToRecoveredDistance","AslaidToRecoveredBearing","RecoveredToPreplotDistance","RecoveredToPreplotBearing","RecoveredToPreplotAlongTrack","RecoveredToPreplotCrossTrack","RecoveryROV", "RecoveryDate",
                            "JulianDay","OnSeabed"]]
            nav_df.fillna(0,inplace=True)
            return nav_df
        except Exception as exc:
            print(f"Checkout this exception: {exc}")
            return None
    else:
        print(f"{file_path} doesn't exist or empty. Returning None.")
        return None

def th_sps_to_df(path_to_sps):
    '''read theretical S or R sps and return dataframe or None'''
    if os.path.exists(path_to_sps):
        extension=os.path.splitext(os.path.split(path_to_sps)[1])[1]
        #print(extension)
        if extension not in ['.s01','.S01','.r01','.R01']:
            print(f'Unknown file extension {extension}')
            return None
        else:
            if extension in ['.r01','.R01']:
                df_out = pd.read_csv(path_to_sps,
                                    skiprows = sps_to_frame_skip(path_to_sps,'R'), sep = '\s+',
                                    names = ['code','Line','Point','idx','Easting','Northing','extras'])
                df_out.drop(columns = ['code','extras'], inplace = True)
                return df_out
            elif extension in ['.s01','.S01']:
                df_out= pd.read_csv(path_to_sps,
                                    skiprows = sps_to_frame_skip(path_to_sps,'S'), sep = '\s+',
                                    names = ['code','Line','Point','idx','Easting_th','Northing_th','extras'])               
                df_out.drop(columns = ['code','extras'], inplace = True)
                return df_out            
    else:
        print(f'No such file {path_to_sps}')
        return None



@exc_time
def source_sps_to_df(path_to_sps):
    '''return source sps as dataframe'''
    if os.path.exists(path_to_sps) and os.stat(path_to_sps).st_size > 0:
        rows_to_skip= sps_to_frame_skip(path_to_sps,'S') 
        try:
            df_out=pd.read_fwf(path_to_sps,
            skiprows = rows_to_skip,
            colspecs = [(0,1),(2,8),(12,18),(23,24),(30,34),(40,46),(47,55),(56,65),
                        (65,71),(71,74),(74,80),(74,87),(81,87),(88,92),(92,95),(95,97),
                        (97,98),(98,99),(99,100),(100,101),(101,102),(103,108)  ],
            names = ['code','Line','Point','Index','GunDepth','WaterDepth','Easting','Northing',
                    'Tide','JulianDay','SpTime','sp_time_ms','ms_fraction','Sequence','Azimuth','SpYear',
                    'DepthEdit','TimingEdit','PressureEdit','RepeatabilityFlag','PositioningFlag','Dither']                          
                    )
            #update df here as well
            df_out['str_time'] = df_out['SpTime'].astype(str)
            df_out['str_fraction'] = df_out['ms_fraction'].astype(str)
            df_out['str_time'] = df_out['str_time'].apply(lambda x: x.zfill(6))
            df_out['str_fraction'] = df_out['str_fraction'].apply(lambda x: x.zfill(6))
            df_out['str_jd'] = df_out['JulianDay'].astype(str)
            df_out['str_jd'] = df_out['str_jd'].apply(lambda x: x.zfill(3))
            df_out["str_datetime"] = df_out["SpYear"].astype(str) + df_out["str_jd"] + df_out["str_time"] + "." + df_out["str_fraction"]
            #df_out["str_datetime"] = df_out["str_datetime"].apply(lambda x: back_to_date(x))
            df_out["SpDateTime"] = df_out["str_datetime"].apply(lambda x: datetime.strptime(x, "%y%j%H%M%S.%f"))
            df_out["SpDateTime"] = pd.to_datetime(df_out.SpDateTime)
            df_out.drop(columns = ['str_time', 'str_jd', 'str_datetime','str_fraction'], inplace = True)
            return df_out
        except Exception as exc:
            print(f"Couldn't produce the data frame from {path_to_sps} d/t {exc}")
            return None
    else:
        print(f"File {os.path.split(path_to_sps)[1]} doesn't exist or empty")
        return None


def get_seq_stats(df_in, seq_nb):
    '''
    get a specific sequence stats
    takes sps_s df as an input
    '''
    assert int(seq_nb) in df_in.Sequence.unique(), f'Incorrect sequence: {seq_nb}'
    assert isinstance(df_in, pd.DataFrame), f'Incorrect input type {type(df_in)}'
    seq_df = df_in.query(f"Sequence == {seq_nb}")
    seq_df["IntershotTime"] = seq_df.SpDateTime.diff()
    seq_df.IntershotTime.fillna(timedelta(seconds = 10), inplace = True)
    sp_number, last, line = len(seq_df), len(seq_df)-1, seq_df.Line.unique()[0] #<= assuming that one sequence has one line only 
    points = list(seq_df.Point)
    fgsp, lgsp = points[0], points[len(points)-1]
    times = list(seq_df.SpDateTime)
    time_start, time_stop = times[0], times[len(times)-1]
    delta_time = times[len(times)-1] - times[0]
    #delta_str = str(times[len(times)-1] - times[0])[7:18]
    delta_sec = round((times[len(times)-1] - times[0]).total_seconds(),2)
    delta_hrs = round((times[len(times)-1] - times[0]).total_seconds()/3600,2)
    coords = (list(seq_df.Easting)[0],list(seq_df.Northing)[0],list(seq_df.Easting)[last],list(seq_df.Northing)[last])
    distance_m =round(dist([coords[0],coords[1]],[coords[2],coords[3]]),2)
    distance_km = round(distance_m/1000, 2)
    avg_speed = round((distance_m/delta_sec) * 3.6, 2)
    ist_avg = seq_df.IntershotTime.mean().total_seconds()
    ist_max = seq_df.IntershotTime.max().total_seconds()
    ist_min = seq_df.IntershotTime.min().total_seconds()
    out_vals = [seq_nb, line, fgsp, lgsp, sp_number, time_start, time_stop, delta_time, delta_hrs, distance_km, avg_speed, ist_avg]
    out_keys = ["SequenceNumber","Line","FirstPoint","LastPoint","PointsNumber","DateTimeStart",
                 "DateTimeStop","TimeDelta","TimeDeltaHours","Distance_km","AverageSpeed","MeanIntershotTime"]
    #line_out = (f"{seq_nb},{line},{fgsp},{lgsp},{sp_number},{time_start},{time_stop},{delta_str},{delta_hrs},{distance_km},{avg_speed},{ist_avg}\n")
    #return(line_out)
    dict_out = dict(zip(out_keys, out_vals))
    return(dict_out)


@exc_time
def make_stats_df(sps_s_df):
    '''make a dataframe from the list of dictionaries'''
    return pd.DataFrame([get_seq_stats(sps_s_df,i) for i in sps_s_df.Sequence.unique()])


def get_line_stats(df_in, line_nb):
    '''get line by line stats from the sequence by sequence df'''
    line_df = df_in.query(f'Line == {line_nb}')
    if len(line_df.SequenceNumber)==1:
    #we have one line per sequence
       return line_df
    else:
        seq_nb = line_df.SequenceNumber.max()
        line_nb = line_df.Line.unique()
        points = list(line_df.FirstPoint)+list(line_df.LastPoint)
        fgsp, lgsp =min(points), max(points)
        points_nb = line_df.PointsNumber.sum()
        line_start = line_df.DateTimeStart.min()
        line_stop = line_df.DateTimeStop.max()
        time_delta = line_df.TimeDelta.sum()
        delta_hrs = line_df.TimeDeltaHours.sum()
        dist_km = line_df.Distance_km.sum()
        avg_speed = line_df.AverageSpeed.mean()
        ist_mean = line_df.MeanIntershotTime.mean()
        out_keys = ["SequenceNumber","Line","FirstPoint","LastPoint","PointsNumber","DateTimeStart",
                 "DateTimeStop","TimeDelta","TimeDeltaHours","Distance_km","AverageSpeed","MeanIntershotTime"]
        out_vals = [seq_nb, line_nb, fgsp, lgsp, points_nb, line_start, line_stop, time_delta, delta_hrs, dist_km, avg_speed, ist_mean]
        line_seq_df = pd.DataFrame(dict(zip(out_keys, out_vals)))
        return(line_seq_df)

def line_stats_df(seqs_stats_df):
    df_out = pd.concat([get_line_stats(seqs_stats_df, i) for i in seqs_stats_df.Line.unique()])
    df_out.reset_index(inplace = True, drop = True)
    return df_out



@exc_time
def get_sequence_stats(df_in):
    '''get basic statistics form the the sequence dataFrame'''
    assert isinstance(df_in, pd.DataFrame), f"Incorrect function afgument type: {type(df_in)}"
    sp_number = len(df_in)
    last = len(df_in)-1
    points = list(df_in.Point)
    fgsp, lgsp = points[0], points[len(points)-1]
    times = list(df_in.SpDateTime)
    delta_str = str(times[len(times)-1] - times[0])[7:18]
    delta_sec = round((times[len(times)-1] - times[0]).total_seconds(),2)
    delta_hrs = round((times[len(times)-1] - times[0]).total_seconds()/3600,2)
    coords = (list(df_in.Easting)[0],list(df_in.Northing)[0],list(df_in.Easting)[last],list(df_in.Northing)[last])
    distance_m =round(dist([coords[0],coords[1]],[coords[2],coords[3]]),2)
    distance_km = round(distance_m/1000, 2)
    avg_speed = round((distance_m/delta_sec) * 3.6, 2)
    ist_avg = df_in.IntershotTime.mean().total_seconds()
    ist_max = df_in.IntershotTime.max().total_seconds()
    ist_min = df_in.IntershotTime.min().total_seconds()
    return(fgsp, lgsp, sp_number, delta_str, delta_sec, delta_hrs, distance_m, distance_km, avg_speed, ist_max, ist_avg, ist_min)


#generate deployment stats dataframe based 

def get_deployment_stats_df(df_in):
    project_start = datetime.strptime("20230218", "%Y%m%d")
    project_timeline = pd.date_range(project_start,datetime.utcnow())
    timeline_df = pd.DataFrame(project_timeline, columns = ["Date"])
    timeline_df["Date"] = timeline_df["Date"].apply(lambda x : x.date())
    timeline_df["Date"] = pd.to_datetime(timeline_df["Date"]) ### <<< = really important!
    timeline_df['JulianDay'] = timeline_df['Date'].apply(lambda x: int(datetime.strftime(x, "%j")))
    counts_df = df_in.groupby("JulianDay").agg({"Point" : 'count'})
    counts_df["NodesDeployed"] = counts_df["Point"]
    counts_df.drop(columns = ["Point"], inplace = True)
    prod_df = pd.merge(timeline_df, counts_df, how = "outer", on = "JulianDay")
    #below dfs for both ROVs
    xlx_df = df_in.query('DeploymentROV == "XLX19"')
    uhd_df = df_in.query('DeploymentROV == "UHD64"')
    xlx_df = xlx_df.groupby("JulianDay").agg({"DeploymentROV" : "count"})
    uhd_df = uhd_df.groupby("JulianDay").agg({"DeploymentROV" : "count"})
    xlx_df.rename(columns={"DeploymentROV":"XLX19"},inplace=True)
    uhd_df.rename(columns={"DeploymentROV":"UHD64"},inplace=True)
    #merge all together
    prod_df = pd.merge(prod_df, xlx_df, how = "outer", on = "JulianDay")
    prod_df = pd.merge(prod_df, uhd_df, how = "outer", on = "JulianDay")
    prod_df.fillna(0, inplace=True)
    prod_df["TotalDeployed"] = (prod_df["NodesDeployed"].cumsum()).astype(int)
    prod_df["TotalByXLX19"] = (prod_df["XLX19"].cumsum()).astype(int)
    prod_df["TotalByUHD64"] = (prod_df["UHD64"].cumsum()).astype(int)
    prod_df["DeploymentComplete"] = round((prod_df["TotalDeployed"]/4071)*100,2)
    prod_df["IncreaseBy"] = round(prod_df["DeploymentComplete"].diff(),2)
    prod_df["XLX19_diff"] = round(prod_df["XLX19"].diff(),2)
    prod_df["UHD64_diff"] = round(prod_df["UHD64"].diff(),2)

    #statistics
    prod_df["rolling_3d_sum"] = prod_df.rolling(window = 3, on = "Date").NodesDeployed.sum()
    prod_df["rolling_3d_avg"] = round(prod_df.rolling(window = 3, on = "Date").NodesDeployed.mean())
    prod_df["rolling_3d_min"] = round(prod_df.rolling(window = 3, on = "Date").NodesDeployed.min(),2)
    prod_df["rolling_3d_max"] = round(prod_df.rolling(window = '3d', on = "Date").NodesDeployed.max(),2)
    
    prod_df.fillna(0.0,inplace = True, axis = 1)

    return(prod_df)

@exc_time
def predict_with_rolling(prod_df):
    dates_df = pd.DataFrame(pd.date_range(prod_df.Date.max(), periods = 6), columns = ["Date"])
    predict_df = pd.merge(prod_df, dates_df, how = "outer", on = "Date")
    std_full = int(predict_df["NodesDeployed"].std())
    std = int(predict_df["NodesDeployed"][len(predict_df) - 9 : len(predict_df) - 6].std())
    print(predict_df["NodesDeployed"][len(predict_df) - 9 : len(predict_df) - 6])
    print(std, std_full)
    predict_df = predict_df[len(predict_df) - 6 :]
    predict_df.fillna(method = "ffill", inplace = True)
    predict_df["rolling_3d_avg"][1:] = predict_df["rolling_3d_avg"][1:].apply(lambda x: add_error(x, error = std))
    predict_df["rolling_3d_min"][1:] = predict_df["rolling_3d_min"][1:].apply(lambda x: add_error(x, error = std))
    predict_df["rolling_3d_max"][1:] = predict_df["rolling_3d_max"][1:].apply(lambda x: add_error(x, error = std))
    return(predict_df)
    
    
    
#generate deployment stats dataframe based 
def get_recovery_stats_df(df_in):
    recovery_start = df_in["RecoveryDate"].min()
    recovery_stop = df_in["RecoveryDate"].max()
    project_timeline = pd.date_range(recovery_start,recovery_stop)
    timeline_df = pd.DataFrame(project_timeline, columns = ["Date"])
    timeline_df["Date"] = timeline_df["Date"].apply(lambda x : x.date())
    #timeline_df.Date = timeline_df.Date.dt.datetime
    timeline_df['JulianDay'] = timeline_df['Date'].apply(lambda x: int(datetime.strftime(x, "%j")))
    counts_df = df_in.groupby("JulianDay").agg({"Point" : 'count'})
    counts_df["NodesRecovered"] = counts_df["Point"]
    counts_df.drop(columns = ["Point"], inplace = True)
    prod_df = pd.merge(timeline_df, counts_df, how = "outer", on = "JulianDay")
    #below dfs for both ROVs
    #xlx_df = df_in.query('DeploymentROV == "XLX19"')
    #uhd_df = df_in.query('DeploymentROV == "UHD64"')
    #xlx_df = xlx_df.groupby("JulianDay").agg({"DeploymentROV" : "count"})
    #uhd_df = uhd_df.groupby("JulianDay").agg({"DeploymentROV" : "count"})
    #xlx_df.rename(columns={"DeploymentROV":"XLX19"},inplace=True)
    #uhd_df.rename(columns={"DeploymentROV":"UHD64"},inplace=True)
    
    #the code below is just for testing purposes
    h13_df = df_in.query('RecoveryROV == "H13"')
    h08_df = df_in.query('RecoveryROV == "H08"')
    sp11_df = df_in.query('RecoveryROV == "SP11"')
    h13_df = h13_df.groupby("JulianDay").agg({"RecoveryROV" : "count"})
    h08_df = h08_df.groupby("JulianDay").agg({"RecoveryROV" : "count"})
    sp11_df = sp11_df.groupby("JulianDay").agg({"RecoveryROV" : "count"})
    h13_df.rename(columns={"RecoveryROV":"H13"},inplace=True)
    h08_df.rename(columns={"RecoveryROV":"H08"},inplace=True)
    sp11_df.rename(columns={"RecoveryROV":"SP11"},inplace=True)
    
    #merge all together
    prod_df = pd.merge(prod_df, h13_df, how = "outer", on = "JulianDay")
    prod_df = pd.merge(prod_df, h08_df, how = "outer", on = "JulianDay")
    prod_df = pd.merge(prod_df, sp11_df, how = "outer", on = "JulianDay")
    prod_df.fillna(0, inplace=True)
    prod_df["TotalRecovered"] = (prod_df["NodesRecovered"].cumsum()).astype(int)
    #prod_df["TotalByXLX19"] = (prod_df["XLX19"].cumsum()).astype(int)
    #prod_df["TotalByUHD64"] = (prod_df["UHD64"].cumsum()).astype(int)
    
    prod_df["TotalByH13"] = (prod_df["H13"].cumsum()).astype(int)
    prod_df["TotalByH08"] = (prod_df["H08"].cumsum()).astype(int)
    prod_df["TotalBySP11"] = (prod_df["SP11"].cumsum()).astype(int)
    prod_df["RecoveryComplete"] = round((prod_df["TotalRecovered"]/4071)*100,2)
    
    return(prod_df)

def get_dates_list(days_number, mode = "past"):
    '''return a list of datetime.date() objects
       where first date is today and last is
       days_number ago or in the future
    '''
    if mode not in ["past", "future"]:
        print("Need correct mode: past or future")
        return None
    elif mode == "past":
        dates = [(datetime.utcnow() - timedelta(days = d)).strftime("%Y-%m-%d") for d in range(0,int(days_number))]
    else:
        dates = [(datetime.utcnow() + timedelta(days = d)).strftime("%Y-%m-%d") for d in range(0,int(days_number))]
    return dates
    
def get_dates_list2(days_number, mode = "past"):
    '''return a list of datetime.date() objects
       where first date is today and last is
       days_number ago or in the future
    '''
    if mode not in ["past", "future"]:
        print("Need correct mode: past or future")
        return None
    elif mode == "past":
        dates = [ datetime((datetime.utcnow() - timedelta(days = d)).date()) for d in range(0,int(days_number))]
    else:
        dates = [(datetime.utcnow() + timedelta(days = d)).date() for d in range(0,int(days_number))]
    return dates

def add_error(number, error=11):
    ''' '''
    return round(number * (random.randint(-error, error)/100+1))
    
#depreciated functions below
@exc_time
def get_seq_stats_df(sps_s_df):
    '''get sequnce by sequnce stats from sps_s df'''
    temp_file = io.StringIO()
    for i in sps_s_df.Sequence.unique():
        temp_file.write(get_sequence_df(sps_s_df,i))
    temp_file.seek(0)
    col_names = ["SequenceNumber","Line","FirstPoint","LastPoint","PointsNumber","DateTimeStart",
                 "DateTimeStop","TimeDeltaStr","TimeDeltaHours","Distance_km","AverageSpeed","MeanIntershotTime"]
    try:
        stats_df = pd.read_csv(temp_file, names = col_names)
        return stats_df
    except Exception as exc:
        print(f"Something went wrong {exc}. Will return None")
        return None




def main():
    df_dep = read_4dnav_for_recovered(fourD_nav)
    print(df_dep.head())
    #print(df_out["DeploymentDate"].min(), df_out["DeploymentDate"].max())
    
    #dates = get_dates_list2(2)
    #print(dates)
    
    #bat_list = [1442,2090,4274,3201,4013,1408,260,2982,3756,1812,1349,720,4503,3364,2363,4977,1282,1769,1068,997,3494,1929,4592,4167,4510,3456,3372,2361,4278,3953,4262,4561,3883,3631,3188,2860,631,5004,3905,2134,3730,3346]
    #code_df = df_dep.query('NodeCode == @bat_list')
    #print(code_df)
    
    #query_df = df_out.query(f'DeploymentDateStr in {dates}')
    #print(query_df)
    #print(query_df.describe())
    #for dt in df_out["RecoveryDateTime"]:
    #    if type(dt) == float:
    #        print(dt, end=" ")
    #df_query = df_out.query('Line == 4819')
    #df_query.dropna(inplace=True)
    #print(df_query)
    
    #counts = get_deployment_stats_df(df_out)
    
    #counts = get_recovery_stats_df(df_out)
    
    #print(predict_with_rolling(counts))
    
    #df_out = source_sps_to_df(all_clean_s)
    #th_sps_s = th_sps_to_df(sps_s_preplot)
    #
    #test_df = df_out.query('Line == 1211')
    #th_test_df = th_sps_s.query('Line == 1211')
    #
    #
    #merge_df = test_df.merge(th_test_df, on = 'Point', how = 'left') 
    #print(merge_df.head())
    #print(len(merge_df))
    #merge_df['radial_distance'] = distance.cdist(list(zip(list(merge_df['Easting']),list(merge_df['Northing']))),list(zip(list(merge_df['Easting_th']),list(merge_df['Northing_th']))),'euclidean')
    #ll = list(zip(list(merge_df['Easting']),list(merge_df['Northing'])))
    #ll2 = list(zip(list(merge_df['Easting_th']),list(merge_df['Northing_th'])))
    #
    #print(ll[:6], len(ll))
    #print(ll2[:6], len(ll))
    #ff = [round(dist(ll[i],ll2[i]),3) for i in range(len(ll))]
    #print(ff[:5], len(ff))
    #merge_df['DistanceToPreplot'] = ff
    #merge_df.drop(columns = ['Line_y', 'idx'], inplace = True)
    #print(merge_df.head())
    #print(merge_df.head())
    #seqs_stats = make_stats_df(df_out)
    #print(seqs_stats)
    #lines_stats = line_stats_df(seqs_stats)
    #print(lines_stats)
    
    #print(l1043.Distance_km.sum())
    #print(stats_df.dtypes)
    
if __name__=="__main__":
    main()