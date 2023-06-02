#standard library imports
import os
from datetime import datetime, timezone, timedelta
#fancy modules imports
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


survey_side_csv = r"X:\Projects\07_BR001522_ARAM_Petrobras\06_SURVEY\26.QC\TO\MT1001522_CumulativeCSV.csv"
fourD_nav = r"Q:\06-ARAM\nav\Postplot_R\4dnav_lines\BR001522_4dnav.csv"
sps_r_preplot = r"Q:\06-ARAM\nav\preplot.r01"

#some custom functions here
def read_4dnav_for_recovered(file_path):
    if os.path.exists(file_path) and os.stat(file_path).st_size != 0:
        try:
            nav_df = pd.read_csv(file_path, skiprows=8)
            nav_df['DeploymentDateTime'] = nav_df["Aslaid Time"].apply(lambda x: datetime.strptime(x, "%Y-%m-%d %H:%M:%S.%f"))
            nav_df['DeploymentDate'] = nav_df['DeploymentDateTime'].apply(lambda x: x.date())
            nav_df.rename(columns={"Preplot Easting":"PreplotEasting","Preplot Northing":"PreplotNorthing",
                                "Preplot Depth":"PreplotDepth","Aslaid Easting":"AslaidEasting","Aslaid Northing":"AslaidNorthing",
                                "Aslaid Depth":"AslaidDepth","Aslaid Tide Offset":"AslaidTideOffset","Aslaid Azimuth":"AslaidAzimuth",
                                "Is Aslaid Adjusted":"IsAslaidAdjusted","Recovered Time":"RecoveryDateTime",
                                "Recovered Easting":"RecoveredEasting","Recovered Northing":"RecoveredNorthing",
                                "Recovered Depth":"RecoveredDepth", "Recovered Tide Offset":"RecoveredTideOffset",
                                "Recovered Azimuth":"RecoveredAzimuth",
                                "Is Recovered Adjusted":"IsRecoveredAdjusted",
                                "Deployed by ROV":"DeploymentROV",
                                "Recovered by ROV":"RecoveryROV"}, inplace=True)
            nav_df.drop(columns=["Aslaid Time","DeployedComments","RecoveredComments"], inplace=True)

            #line below should be edited
            #nav_df = nav_df.query('Line ! = 4819')
            # filter the unrecovered with the recovery time
            nav_df = nav_df[nav_df["RecoveryDateTime"] == nav_df["RecoveryDateTime"]]
            nav_df["RecoveryDateTime"] = nav_df["RecoveryDateTime"].apply(lambda x: datetime.strptime(x, "%Y-%m-%d %H:%M:%S.%f"))
            nav_df["RecoveryDate"] = nav_df["RecoveryDateTime"].apply(lambda x: x.date())
            nav_df['JulianDay'] = nav_df['RecoveryDate'].apply(lambda x: int(datetime.strftime(x, "%j")))
            nav_df["OnSeabed"] = (nav_df["RecoveryDate"] - nav_df["DeploymentDate"]).dt.days + 1
            nav_df['JulianDay'] = nav_df['RecoveryDate'].apply(lambda x: int(datetime.strftime(x, "%j")))
            nav_df["RecoveryDateStr"] = nav_df['RecoveryDate'].apply(lambda x: datetime.strftime(x, "%Y-%m-%d"))
            nav_df = nav_df[["Line","Point","NodeCode","Index","PreplotEasting","PreplotNorthing", "RecoveryDateTime", 
                            "RecoveredEasting","RecoveredNorthing","RecoveredDepth","RecoveredTideOffset","RecoveredAzimuth","IsRecoveredAdjusted",
                            "AslaidToRecoveredDistance","AslaidToRecoveredBearing","RecoveredToPreplotDistance",
                            "RecoveredToPreplotBearing","RecoveredToPreplotAlongTrack","RecoveredToPreplotCrossTrack",
                            "RecoveryROV", "RecoveryDate",
                            "JulianDay","OnSeabed","RecoveryDateStr"]]
            nav_df.fillna(0,inplace=True)
            return nav_df
        except Exception as exc:
            print(f"Checkout this exception: {exc}")
            return None
    else:
        return None

#below function needs to be tweaked after recovery start

def get_recovery_stats_df(df_in):
    recovery_start = df_in["RecoveryDate"].min()
    recovery_stop = df_in["RecoveryDate"].max()
    project_timeline = pd.date_range(recovery_start,recovery_stop)
    timeline_df = pd.DataFrame(project_timeline, columns = ["Date"])
    timeline_df["Date"] = timeline_df["Date"].apply(lambda x : x.date())
    timeline_df["Date"] = pd.to_datetime(timeline_df["Date"])                   #important to convert
    timeline_df['JulianDay'] = timeline_df['Date'].apply(lambda x: int(datetime.strftime(x, "%j")))
    counts_df = df_in.groupby("JulianDay").agg({"Point" : 'count'})
    counts_df["NodesRecovered"] = counts_df["Point"]
    counts_df.drop(columns = ["Point"], inplace = True)
    prod_df = pd.merge(timeline_df, counts_df, how = "outer", on = "JulianDay")
    #below dfs for both ROVs
    xlx_df = df_in.query('RecoveryROV == "XLX19"')
    uhd_df = df_in.query('RecoveryROV == "UHD64"')
    xlx_df = xlx_df.groupby("JulianDay").agg({"RecoveryROV" : "count"})
    uhd_df = uhd_df.groupby("JulianDay").agg({"RecoveryROV" : "count"})
    xlx_df.rename(columns={"RecoveryROV":"XLX19"},inplace=True)
    uhd_df.rename(columns={"RecoveryROV":"UHD64"},inplace=True)
    
    #the code below is just for testing purposes
    #h13_df = df_in.query('RecoveryROV == "H13"')
    #h08_df = df_in.query('RecoveryROV == "H08"')
    #sp11_df = df_in.query('RecoveryROV == "SP11"')
    #h13_df = h13_df.groupby("JulianDay").agg({"RecoveryROV" : "count"})
    #h08_df = h08_df.groupby("JulianDay").agg({"RecoveryROV" : "count"})
    #sp11_df = sp11_df.groupby("JulianDay").agg({"RecoveryROV" : "count"})
    #h13_df.rename(columns={"RecoveryROV":"H13"},inplace=True)
    #h08_df.rename(columns={"RecoveryROV":"H08"},inplace=True)
    #sp11_df.rename(columns={"RecoveryROV":"SP11"},inplace=True)
    
    #merge all together
    prod_df = pd.merge(prod_df, xlx_df, how = "outer", on = "JulianDay")
    prod_df = pd.merge(prod_df, uhd_df, how = "outer", on = "JulianDay")
    #prod_df = pd.merge(prod_df, sp11_df, how = "outer", on = "JulianDay")
    prod_df.fillna(0, inplace=True)
    prod_df["TotalRecovered"] = (prod_df["NodesRecovered"].cumsum()).astype(int)
    prod_df["TotalByXLX19"] = (prod_df["XLX19"].cumsum()).astype(int)
    prod_df["TotalByUHD64"] = (prod_df["UHD64"].cumsum()).astype(int)
    
    prod_df["XLX19_diff"] = round(prod_df["XLX19"].diff(),2)
    prod_df["UHD64_diff"] = round(prod_df["UHD64"].diff(),2)
    
    #prod_df["TotalByH13"] = (prod_df["H13"].cumsum()).astype(int)
    #prod_df["TotalByH08"] = (prod_df["H08"].cumsum()).astype(int)
    #prod_df["TotalBySP11"] = (prod_df["SP11"].cumsum()).astype(int)
    #prod_df["H13_diff"] = round(prod_df["H13"].diff(),2)
    #prod_df["H08_diff"] = round(prod_df["H08"].diff(),2)

    return(prod_df)

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


@st.cache_data          #cache the dataframe that is not going to change
def th_sps_to_df(path_to_sps):
    '''read theretical S or R sps and return a frame'''
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
                                    names = ['code','Line','Point','idx','Easting','Northing','extras'])               
                df_out.drop(columns = ['code','extras'], inplace = True)
                return df_out            
    else:
        print(f'No such file {path_to_sps}')
        return None

#a small auxiliary function 
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


#basic application page config
st.set_page_config(
    page_title=f"Recovery overview",
    page_icon=":turtle:",
    layout="wide",
    menu_items = {'Get Help': "https://docs.streamlit.io",
    "Report a bug": "https://docs.streamlit.io/library/cheatsheet",
    "About":'# Really have *no idea* what that is!'}
    )

" # :green[Recovery overview]"
(f" ##### :green[Current date and time: {datetime.strftime(datetime.utcnow(), '%Y-%m-%d %H:%M')} UTC]")
m_time = datetime.strftime(datetime.fromtimestamp(os.stat(survey_side_csv).st_mtime,tz = timezone.utc), '%Y-%m-%d %H:%M') #check actual m_time rather then time of last QGIS update
m_jd = datetime.strftime(datetime.fromtimestamp(os.stat(survey_side_csv).st_mtime,tz = timezone.utc), '%j')
(f" ###### :green[Input data last updated: {m_time} UTC. Julian Day: {m_jd}.]")

preplot_df = th_sps_to_df(sps_r_preplot)
recovered_df = read_4dnav_for_recovered(fourD_nav)
counts_df = get_recovery_stats_df(recovered_df)


dates_list = get_dates_list(2)
days_df = recovered_df.query(f'RecoveryDateStr in {dates_list}')


if st.checkbox("Show raw data for Recovered nodes"):
    st.text(f"Source: {fourD_nav}")
    #st.text("Nothing here at the moment")
    st.dataframe(recovered_df)

if st.checkbox("Show raw data for Recovery Counts"):
    st.text(f"Source: {fourD_nav}")
    #st.text("Nothing here at the moment")
    st.dataframe(counts_df)

#plotting block
#overview tab block

# progress map graphical object API
progress_map_go = go.Figure()
progress_map_go.add_trace(go.Scatter(x =preplot_df["Easting"], y = preplot_df["Northing"], mode = "markers", marker=dict(color = "gray", opacity = 0.8, size = 4), hoverinfo = "skip", name = f"To recover: {4071 - len(recovered_df)}"))

progress_map_go.add_trace(go.Scatter(x = recovered_df['RecoveredEasting'], y = recovered_df['RecoveredNorthing'], text = (recovered_df["NodeCode"]), name = f"Before: {len(recovered_df)}", mode = "markers", marker = dict(symbol = "pentagon", color = "Gold", size = 6),
                customdata = np.stack((recovered_df.Line, recovered_df.Point, recovered_df.RecoveryROV,recovered_df.RecoveryDate, recovered_df.JulianDay, recovered_df.Index), axis=-1), legendrank = 900,
                hovertemplate = '''<b><i>Node info</i></b><br><b>Line: %{customdata[0]} </b><b>Point: %{customdata[1]} Index: %{customdata[5]}</b><br><b>Bumper: %{text}</b><br><b>Recovered by: %{customdata[2]}</b><br><b>Recovered at: %{customdata[3]}, JD: %{customdata[4]}</b><extra></extra>'''))

progress_map_go.add_trace(go.Scatter(x =days_df['RecoveredEasting'], y = days_df['RecoveredNorthing'], mode = "markers", marker=dict(color = "green", symbol = "pentagon", opacity = 0.8, size = 8), legendrank = 800,
                hoverinfo = "skip", name = f"Last {len(dates_list)} days: {len(days_df)}"))

progress_map_go.update_layout(title = "<b>Recovery progress</b>", xaxis_title = "<b><i>Easting (m)</i></b>", yaxis_title = "<b><i>Northing (m)</i></b>", legend_title_text = "<i>Recovered:</i>",
                        font = dict(family="Courier New, monospace", size=14, color="RoyalBlue"), legend = {"itemsizing": "constant"}, width = 1000, height = 800)

# dive time go API
dive_time_go = go.Figure()
dive_time_go.add_trace(go.Scatter(x =preplot_df.Easting, y = preplot_df.Northing, mode = "markers", marker=dict(color = "gray", opacity = 0.8, size = 4), 
             hoverinfo = "skip", name = "Not deployed", showlegend = False))
dive_time_go.add_trace(go.Scatter(x = recovered_df.RecoveredEasting, y = recovered_df.RecoveredNorthing, mode = "markers", showlegend = False, marker = dict(size = 8, color = recovered_df.OnSeabed, symbol = "pentagon",colorscale = "Rainbow", showscale = True),
             customdata = np.stack((recovered_df.Line, recovered_df.Point, recovered_df.Index, recovered_df.OnSeabed,recovered_df.RecoveryDate, recovered_df.JulianDay,recovered_df.NodeCode), axis=-1),
             hovertemplate = '''<b><i>Node info</i></b><br><b>Line: %{customdata[0]} </b><b>Point: %{customdata[1]} Index: %{customdata[2]}<br><b>Bumper: %{customdata[5]}</b><br><b>Days on seabed: %{customdata[3]}</b><br><b>Recovered at: %{customdata[4]}, JD: %{customdata[4]}</b><extra></extra>'''))

dive_time_go.update_layout(title = "<b>Seabed time (days)</b>", xaxis_title = "<b><i>Easting (m)</i></b>", yaxis_title = "<b><i>Northing (m)</i></b>", 
                        font = dict(family="Courier New, monospace", size=14, color="RoyalBlue"), width = 1000, height = 800)


#water depths map go API
water_depths_go = go.Figure()
water_depths_go.add_trace(go.Scatter(x =preplot_df.Easting, y = preplot_df.Northing, mode = "markers", marker=dict(color = "gray", opacity = 0.8, size = 4), hoverinfo = "skip", name = "Not deployed", showlegend = False))
water_depths_go.add_trace(go.Scatter(x = recovered_df.RecoveredEasting, y = recovered_df.RecoveredNorthing, mode = "markers", showlegend = False, marker = dict(size = 8, color = recovered_df.RecoveredDepth, symbol = "pentagon",colorscale = "Rainbow", showscale = True),
                customdata = np.stack((recovered_df.Line, recovered_df.Point, recovered_df.RecoveredDepth,recovered_df.RecoveryDate, recovered_df.JulianDay,recovered_df.NodeCode), axis=-1),
                hovertemplate = '''<b><i>Node info</i></b><br><b>Line: %{customdata[0]}, </b><b>Point: %{customdata[1]}</b><br><b>Bumper: %{customdata[5]}</b><br><b>Recovery Depth: %{customdata[2]}</b><br><b>Recovered at: %{customdata[3]}, JD: %{customdata[4]}</b><extra></extra>'''))
                                            
water_depths_go.update_layout(title = "<b>Recovery depth (m)</b>", xaxis_title = "<b><i>Easting (m)</i></b>", yaxis_title = "<b><i>Northing (m)</i></b>", 
                            font = dict(family="Courier New, monospace", size=14, color="RoyalBlue"), width = 1000, height = 800)

#radial offsets go API
preplot_recovery_offsets_go = go.Figure()
preplot_recovery_offsets_go.add_trace(go.Scatter(x =preplot_df.Easting, y = preplot_df.Northing, mode = "markers", marker=dict(color = "gray", opacity = 0.8, size = 4), 
                            hoverinfo = "skip", name = "Not deployed", showlegend = False))
preplot_recovery_offsets_go.add_trace(go.Scatter(x = recovered_df.RecoveredEasting, y = recovered_df.RecoveredNorthing, mode = "markers", showlegend = False, marker = dict(size = 8, color = recovered_df.RecoveredToPreplotDistance, symbol = "pentagon", colorscale = "Rainbow", showscale = True),
                            customdata = np.stack((recovered_df.Line, recovered_df.Point, recovered_df.RecoveredToPreplotDistance, recovered_df.RecoveryDate, recovered_df.JulianDay, recovered_df.NodeCode), axis=-1),
                            hovertemplate = '''<b><i>Node info</i></b><br><b>Line: %{customdata[0]}, </b><b>Point: %{customdata[1]}</b><br><b>Bumper: %{customdata[5]}</b><br><b>Radial offset: %{customdata[2]} m</b><br><b>Recovered at: %{customdata[3]}, JD: %{customdata[4]}</b><extra></extra>'''))
                                            
preplot_recovery_offsets_go.update_layout(title = "<b>Preplot to Recovery position offset (m)</b>", xaxis_title = "<b><i>Easting (m)</i></b>", yaxis_title = "<b><i>Northing (m)</i></b>", 
                            font = dict(family="Courier New, monospace", size=14, color="RoyalBlue"), width = 1000, height = 800)



#recovery counts tab block

#plotly graphical object API
daily_recovered_go = go.Figure()
daily_recovered_go.add_trace(go.Bar(x = counts_df["Date"], y = counts_df["NodesRecovered"], name = "<b>Total</b>", 
                hovertemplate = '''<br><b>Date: </b>%{x}<br><b>Daily production: %{y} </b><br>'''))

daily_recovered_go.add_trace(go.Scatter(x = counts_df["Date"], y = counts_df["XLX19"], mode = "lines+markers", name = "XLX19", text = counts_df.XLX19_diff, 
                    hovertemplate = '''<br><b>XLX19</b><br><b>Nodes recovered: </b>%{y}<br><b>Daily change: </b>%{text:.2f}<extra></extra>'''))
daily_recovered_go.add_trace(go.Scatter(x = counts_df["Date"], y = counts_df["UHD64"], mode = "lines+markers", text = counts_df.UHD64_diff, name = "UHD64", 
                    hovertemplate = '''<br><b>UHD64</b><br><b>Nodes recovered: </b>%{y}<br><b>Daily change: </b>%{text:.2f}<extra></extra>'''))

daily_recovered_go.add_shape(type = "line", line_color = "green", line_width = 3, opacity = 0.5, x0=counts_df["Date"].min(), x1=counts_df["Date"].max(), y0 = 100, y1 = 100)
daily_recovered_go.add_annotation(text = "<b>Daily target (100 nodes)</b>" , x = datetime(2023, 4, 21), y = 102, arrowhead = 3, arrowcolor = "green", showarrow = True)

daily_recovered_go.update_layout(hovermode = 'x unified', width = 1000, height = 800, title = "<b>Daily recovery</b>", hoverdistance = 300,
                                xaxis_title = "<b><i>Date</i></b>", yaxis_title = "<b><i>Production</i></b>", font = dict(family="Courier New, monospace", size=14, color="RoyalBlue"))


# below plot is just for the test
#cumsum_recovered = px.line(counts_df,x = "Date", y = "TotalRecovered", markers = True, title = f"<b>Recovered Cumulative sum</b>",hover_data = {"JulianDay": True},width = 1000, height = 800)
#cumsum_recovered.add_trace(go.Scatter(x = counts_df["Date"], y = counts_df["TotalByXLX19"], mode = "lines+markers", name = "XLX19", hovertemplate = '''<b>Date: </b>%{x}<br><b>Total recovered: </b>%{y}<br>'''))
#cumsum_recovered.add_trace(go.Scatter(x = counts_df["Date"], y = counts_df["TotalByUHD64"], mode = "lines+markers", name = "UHD64", hovertemplate = '''<b>Date: </b>%{x}<br><b>Total recoverd: </b>%{y}<br>'''))
#cumsum_recovered.add_trace(go.Scatter(x = counts_df["Date"], y = counts_df["TotalBySP11"], mode = "lines+markers", name = "SP11", hovertemplate = '''<b>Date: </b>%{x}<br><b>Total recovered: </b>%{y}<br>'''))
#cumsum_recovered.update_layout(hovermode = 'x unified')

# NEED TO SWAP TO THE go API PLOT BELOW WHEN there is actual RECOVERY
cumsum_recovered_go = go.Figure()
cumsum_recovered_go.add_trace(go.Scatter( x = counts_df.Date, y = counts_df.TotalRecovered, mode = "lines+markers", name = "<b><i>Total</i></b>",
                            hovertemplate = '''<br><b>Date: </b>%{x}<br><b>Total recovered: %{y}</b><br>'''))
cumsum_recovered_go.add_trace(go.Scatter(x = counts_df.Date, y = counts_df.TotalByXLX19, mode = "lines+markers", name = "<b>XLX19</b>", 
                            hovertemplate = '''<br><b>Date: </b>%{x}<br><b>Total recovered: <i>%{y}</i></b><br>'''))
cumsum_recovered_go.add_trace(go.Scatter(x = counts_df.Date, y = counts_df.TotalByUHD64, mode= 'lines+markers', name = "<b>UHD64</b>", 
                            hovertemplate = '''<br><b>Date: </b>%{x}<br><b>Total recovered: <i>%{y}</i></b><br>'''))

cumsum_recovered_go.update_layout(hovermode = 'x unified', width = 1000, height = 800, title = "<b>Cumulative recovery sum</b>",
                             xaxis_title = "<b><i>Date</i></b>", hoverdistance = 500,
                             yaxis_title = "<b><i>Production</i></b>", font = dict(family="Courier New, monospace", size=14, color="RoyalBlue"))

#rov destribution map NOT NEEDED
rov_destribution = px.scatter(recovered_df, x = 'RecoveredEasting', y = 'RecoveredNorthing', color = "RecoveryROV",symbol="RecoveryROV", title = f"<b>Recovered by ROV</b>", 
                  hover_data = {'RecoveredEasting': False, 'RecoveredNorthing': False, 'Line': True, 'Point': True, "RecoveryROV": True, 'JulianDay':True, "RecoveryDate":True }, width = 1000, height = 800)


#tabs block
overview_tab, counts_tab, attrs_tab = st.tabs(["**Recovery overview**", "**Recovery counts**", "**Line attributes**"])

with overview_tab:
    col1, col2 = st.columns(2)
    with col1:
        #st.text("Some attributes scatter here")
        st.plotly_chart(progress_map_go, theme = None, use_container_width = False)
        st.plotly_chart(water_depths_go, theme = None, use_container_width = False)
        
    with col2:
        st.plotly_chart(dive_time_go, theme = None, use_container_width = False)
        st.plotly_chart(preplot_recovery_offsets_go, theme = None, use_container_width = False)
        #st.text("Another attributes scatter here")
        #st.plotly_chart(water_depths, theme = None, use_container_width = False)
        #st.plotly_chart(preplot_recovery_bearing, theme = None, use_container_width = False)

with counts_tab:
    col1, col2 = st.columns(2)
    with col1:
        #st.text("Bar chart here")
        st.plotly_chart(daily_recovered_go, theme = None, use_container_width = False)
        st.plotly_chart(rov_destribution, theme = None, use_container_width = False)
    with col2:
        st.plotly_chart(cumsum_recovered_go, theme = None, use_container_width = False)
        #st.text("Line comulative chart here")

with attrs_tab:
    " ## :green[Line by Line attributes]"
    lines = recovered_df.Line.unique()
    line_to_choose = st.selectbox("", lines)
    line_df = recovered_df.query(f'Line == {line_to_choose}')
    th_line_df = preplot_df.query(f'Line == {line_to_choose}')
    #
    recovered = len(line_df)
    to_recover = len(th_line_df)
    col1, col2 = st.columns(2)
    ratio = round(recovered/to_recover*100)
    ttl = f"Nodes recovered: {recovered} of {to_recover} ({ratio}%)"
    with col1:
        # attrs plot
        attr_plot_go = make_subplots(rows=2, cols=2, start_cell="top-left", subplot_titles = ("Recovery time", "Recovery Depth (m)", "Radial offset (m)", "Tide (m)"))
        attr_plot_go.add_trace(go.Scatter(x = line_df.Point, y = line_df.RecoveryDateTime, mode = "lines+markers", name = "<b><i>Time vs point</i></b>", showlegend = False,
                     hovertemplate = '''<br><b>Point: %{x}<br>Recovery time: %{y}</b><extra></extra>'''),row = 1, col =1)
        attr_plot_go.add_trace(go.Scatter(x = line_df.Point, y = line_df.RecoveredDepth*-1, mode = "lines+markers", name = "<b><i>Depth vs Point (m)</i></b>", showlegend = False,
                     hovertemplate = '''<br><b>Point: %{x}<br>Depth: %{y} m</b><extra></extra>'''), row = 1, col = 2)
        attr_plot_go.add_trace(go.Scatter(x = line_df.Point, y = line_df.RecoveredToPreplotDistance, mode = "lines+markers", name = "<b><i>Offset vs point (m)</i></b>", showlegend = False,
                     customdata = np.stack((line_df.RecoveredToPreplotAlongTrack, line_df.RecoveredToPreplotCrossTrack), axis = -1),
                     hovertemplate = '''<br><b>Point: %{x}<br><i>Offsets:<br>Radial: %{y} m<br>Xline: %{customdata[1]} m<br>Crossline: %{customdata[0]} m</b><extra></extra>'''), row = 2, col = 1)
        attr_plot_go.add_trace(go.Scatter(x = line_df.Point, y = line_df.RecoveredTideOffset, mode = "lines+markers", name = "<b><i>Tide vs point</i></b>", showlegend = False,
                     hovertemplate = '''<br><b>Point: %{x}<br>Tide: %{y} m</b><extra></extra>'''), row = 2, col = 2)
        attr_plot_go.update_layout(width = 1000, height = 800, title = f"<b>Line {line_to_choose} attributes</b>", font = dict(family="Courier New, monospace", size=14, color="RoyalBlue"))
        
        # display plot
        st.plotly_chart(attr_plot_go, theme = None, use_container_width = False)
        
    with col2:
        # position map
        # plot the line position relative to preplot
        progress_map_go = go.Figure()
        progress_map_go.add_trace(go.Scatter(x =preplot_df.Easting, y = preplot_df.Northing, mode = "markers", marker=dict(color = "gray", symbol = "pentagon", opacity = 0.6, size = 6), hoverinfo = "skip", name = "Preplot"))
        progress_map_go.add_trace(go.Scatter(x = line_df.RecoveredEasting, y = line_df.RecoveredNorthing, text = line_df.NodeCode, name = "Current Line", mode = "markers", marker = dict(symbol = "pentagon", color = "SpringGreen", size = 8),
                       customdata = np.stack((line_df.Line, line_df.Point, line_df.RecoveryROV,line_df.RecoveryDate, line_df.JulianDay, line_df.Index), axis=-1), legendrank = 900,
                       hovertemplate = '''<b><i>Node info</i></b><br><b>Line: %{customdata[0]} </b><b>Point: %{customdata[1]} Index: %{customdata[5]}</b><br><b>Bumper: %{text}</b><br><b>Recovered by: %{customdata[2]}</b><br><b>Recovered at: %{customdata[3]}, JD: %{customdata[4]}</b><extra></extra>'''))
        progress_map_go.update_layout(title = f"<b>{ttl}</b>", xaxis_title = "<b><i>Easting (m)</i></b>", yaxis_title = "<b><i>Northing (m)</i></b>", 
                       font = dict(family="Courier New, monospace", size=14, color="RoyalBlue"), width = 1000, height = 800)
        
        # display plot
        st.plotly_chart(progress_map_go, theme = None, use_container_width = False)