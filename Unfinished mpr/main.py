from galvani import BioLogic
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import os
import plotly.graph_objs as go
pd.set_option('display.max_columns', None)

def identify_eclab_files(directory):
    mpr_file = None
    mpl_file = None
    for file in os.listdir(directory):
        if file.endswith('.mpr'):
            mpr_file = os.path.join(directory, file)
        elif file.endswith('.mpl'):
            mpl_file = os.path.join(directory, file)
        #if not mpr_file or not mpl_file:
            #raise FileNotFoundError("MPR or MPL file not found in the provided folder.")

    return mpr_file, mpl_file


def eclab_voltage(processed_voltage_df, start_time, end_time):
    # Ensure start_time and end_time are in datetime format
    start_time = pd.to_datetime(start_time)
    end_time = pd.to_datetime(end_time)

    # Filter DataFrame between start_time and end_time
    volt_df = processed_voltage_df[
        (processed_voltage_df['Timestamp'] >= start_time) & (processed_voltage_df['Timestamp'] <= end_time)]

    return volt_df

def process_eclab(directory):

    print('Processing MPR file')

    eclabfiles = identify_eclab_files(directory)
    mpr_file_path = eclabfiles[0]
    mpl_file = eclabfiles[1]
    mpr_file = BioLogic.MPRfile(mpr_file_path)

    df = pd.DataFrame(mpr_file.data)
    print(df)

    def extract_start_time(mpl_file_path):
        # Extracts the start time from an MPL file
        with open(mpl_file_path, 'r', encoding='ISO-8859-1') as file:
            for line in file:
                if line.startswith('Acquisition started on :'):
                    timestamp = line.split(':')[1].strip()
                    return pd.to_datetime(timestamp)

    # Convert 'Q charge/discharge' values to absolute values
    df['Abs_Q_charge_discharge'] = df['Q charge/discharge/mA.h'].abs()

    # Map half cycles to full cycle numbers, ensuring half cycles 0 and 1 are mapped to full cycle 1
    df['Full_Cycle_Number'] = ((df['half cycle'] // 2) + 1).astype(int)

    is_charge = df['half cycle'] % 2 == 0  # If first cycle (0) is charge, then this is true
    is_discharge = ~is_charge  # The opposite for discharge cycles

    charge_capacity = df[is_charge].groupby('Full_Cycle_Number')['Abs_Q_charge_discharge'].max()
    discharge_capacity = df[is_discharge].groupby('Full_Cycle_Number')['Abs_Q_charge_discharge'].max()

    coulombic_efficiency = (discharge_capacity / charge_capacity) * 100

    if not mpl_file:
        print('no mpl')
        start_time = pd.to_datetime(mpr_file.timestamp)
        print(start_time)
    else:
        print('mpl found')
        start_time = extract_start_time(mpl_file)

    df['Absolute_Time_UTC'] = df['time/s'].apply(lambda s: start_time + timedelta(seconds=s))

    time = df.groupby('Full_Cycle_Number')['time/s'].max()
    time_utc = df.groupby('Full_Cycle_Number')['Absolute_Time_UTC'].max()

    cycle_numbers = charge_capacity.index.union(discharge_capacity.index)
    processed_cycle_df = pd.DataFrame({
        'Cycle_Number': cycle_numbers,
        'Charge_Capacity': charge_capacity.reindex(cycle_numbers, fill_value=0),
        'Discharge_Capacity': discharge_capacity.reindex(cycle_numbers, fill_value=0),
        'Coulombic Efficiency': coulombic_efficiency.reindex(cycle_numbers, fill_value=100),  # Default to 100% efficiency if no data
        'Time': time.reindex(cycle_numbers, fill_value=0),
        'Timestamp': time_utc.reindex(cycle_numbers, fill_value=0)
    })

    full_time = df['time/s']
    full_volt = df['Ewe/V']
    full_time_utc = df['Absolute_Time_UTC']
    processed_voltage_df = pd.DataFrame({
        'Time':full_time,
        'Timestamp':full_time_utc,
        'Voltage':full_volt
    })
    print('MPR Processed')
    return processed_cycle_df, processed_voltage_df

def create_voltage_trace(df):
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df['Voltage'],
        y=df['Timestamp'],
        mode='lines',
        line=dict(color='Red')
    ))

    fig.update_layout(
        title="Voltage Trace",
        xaxis_title="Voltage (V)",
        yaxis_title="Time"
    )

    return fig

past_start_datetime = '2024-02-21 02:16'
past_end_datetime = '2024-02-21 05:00'
start_datetime = datetime.strptime(past_start_datetime, '%Y-%m-%d %H:%M')
end_datetime = datetime.strptime(past_end_datetime, '%Y-%m-%d %H:%M')
df = process_eclab(r"C:\Users\fionn\PyCharmProjects\galvani\finished_mpr")

volt = df[1]
print(volt)
volt_df = eclab_voltage(volt,start_datetime,end_datetime)
print(volt_df)
create_voltage_trace(volt_df)