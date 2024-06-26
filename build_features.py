import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from DataTransformation import LowPassFilter, PrincipalComponentAnalysis
from TemporalAbstraction import NumericalAbstraction
from FrequencyAbstraction import FourierTransformation
from sklearn.cluster import KMeans

# --------------------------------------------------------------
# Load data
# --------------------------------------------------------------

df = pd.read_pickle("../../data/interim/02_outliers_removed_chauvenets.pkl")

predictor_columns = list(df.columns[:6])

#  Plot Settings
plt.style.use("fivethirtyeight")
plt.rcParams["figure.figsize"] = (20, 5)
plt.rcParams["figure.dpi"] = 100
plt.rcParams["lines.linewidth"] = 2


# Example of a plot for a subset
df.info()
subset = df[df["set"] == 35]["gyr_y"].plot()


# --------------------------------------------------------------
# Dealing with missing values (imputation)
# --------------------------------------------------------------

# INTERPOLATE will fill in the gap were the data is missing.
for col in predictor_columns:
    df[col] = df[col].interpolate()
    
df.info()


# --------------------------------------------------------------
# Calculating set duration
# --------------------------------------------------------------

df[df["set"] == 25]["acc_y"].plot()
df[df["set"] == 50]["acc_y"].plot()

#  Time of the 'LAST-Index' minus Time of the 'FIRST-Index'
duration = df[df["set"] == 1].index[-1] - df[df["set"] == 1].index[0] 
duration.seconds

#  LOOP to find the average DURATION among the unique sets
for s in df["set"].unique():

    start = df[df["set"] == s].index[0]
    stop = df[df["set"] == s].index[-1]
    
    duration =  stop - start
    df.loc[(df["set"] == s), "duration"] = duration.seconds

duration_df = df.groupby(["category"])["duration"].mean()

duration_df.iloc[0] / 5

duration_df.iloc[1] / 10

# --------------------------------------------------------------
# Butterworth lowpass filter
# --------------------------------------------------------------

df_lowpass = df.copy()
LowPass = LowPassFilter()

fs = 1000/200
# cutoff frequency
cutoff = 1.45

df_lowpass = LowPass.low_pass_filter(df_lowpass, "acc_y", fs, cutoff, order=5)

subset = df_lowpass[df_lowpass["set"] == 45]
print(subset["label"][0])

#  Code for Data Visiulation
fig, ax = plt.subplots(nrows=2, sharex=True, figsize=(20, 10))
ax[0].plot(subset["acc_y"].reset_index(drop=True), label="raw data")
ax[1].plot(subset["acc_y_lowpass"].reset_index(drop=True), label="butterworth filter")
ax[0].legend(loc="upper center", bbox_to_anchor=(0.5, 1.15), fancybox=True, shadow=True)
ax[1].legend(loc="upper center", bbox_to_anchor=(0.5, 1.15), fancybox=True, shadow=True)


for col in predictor_columns:
    # Here we add a col for the _lowpass values
    df_lowpass = LowPass.low_pass_filter(df_lowpass, col, fs, cutoff, order=5)
    # Here we override the inital columns with the values from the lowpass columns
    df_lowpass[col] = df_lowpass [col + "_lowpass"]
    # Here we delete the extreme _lowpass columns. 
    del df_lowpass[col + "_lowpass"]    
    


# --------------------------------------------------------------
# Principal component analysis PCA
# --------------------------------------------------------------

df_pca = df_lowpass.copy()
PCA = PrincipalComponentAnalysis()
pc_values = PCA.determine_pc_explained_variance(df_pca, predictor_columns)
    

plt.figure(figsize=(10,10))
plt.plot(range(1, len(predictor_columns) +1), pc_values)
plt.xlabel("principla component number")
plt.ylabel("explained variance")
plt.show()

df_pca = PCA.apply_pca(df_pca, predictor_columns, 3)

subset = df_pca[df_pca["set"] == 35]

subset[["pca_1", "pca_2", "pca_3"]]
subset[["pca_1", "pca_2", "pca_3"]].plot()


# --------------------------------------------------------------
# Sum of squares attributes
# --------------------------------------------------------------

df_squared = df_pca.copy()

acc_r = (df_squared["acc_x"] ** 2) + (df_squared["acc_y"] ** 2) + (df_squared["acc_z"] ** 2)
gyr_r = (df_squared["gyr_x"] ** 2) + (df_squared["gyr_y"] ** 2) + (df_squared["gyr_z"] ** 2)

df_squared["acc_r"] = np.sqrt(acc_r)
df_squared["gyr_r"] =  np.sqrt(gyr_r)

subset = df_squared[df_squared["set"] == 41]

subset[["acc_r", "gyr_r"]].plot()
subset[["acc_r", "gyr_r"]].plot(subplots=True)

# --------------------------------------------------------------
# Temporal abstraction
# --------------------------------------------------------------

df_temporal = df_squared.copy()

NumAbs = NumericalAbstraction()

#  Use this as the DATA_TABLE variable in in NumericalAbstraction()
predictor_columns = predictor_columns + ["acc_r", "gyr_r"]

#  Use this as WINDOW_SIZE variable in NumericalAbstraction()
# This is the space before the index. Note, that the window will start after your initial step. So a window size of 5 steps will skip the first 4 values, but use them to create the average for step 5. 
ws = int(1000 /200)

for col in predictor_columns:
    df_temporal = NumAbs.abstract_numerical( df_temporal, [col], ws, "mean")
    df_temporal = NumAbs.abstract_numerical( df_temporal, [col], ws, "std")

df_temporal_list = []
for s in df_temporal["set"].unique():
    subset = df_temporal[df_temporal["set"] == s].copy()
    for col in predictor_columns:
        subset = NumAbs.abstract_numerical( subset, [col], ws, "mean")
        subset = NumAbs.abstract_numerical( subset, [col], ws, "std")
    df_temporal_list.append(subset)
    
df_temporal = pd.concat(df_temporal_list)
     
     
subset[["acc_y", "acc_y_temp_mean_ws_5", "acc_y_temp_std_ws_5"]].plot()
subset[["gyr_y", "gyr_y_temp_mean_ws_5", "gyr_y_temp_std_ws_5"]].plot()

# --------------------------------------------------------------
# Frequency features
# --------------------------------------------------------------

df_freq = df_temporal.copy().reset_index()

FreqAbs = FourierTransformation()

# the sampling rate expresses the number of samples per second (i.e. Frequency is Hertz of the dataset)
fs = int(1000 / 200)
ws = int(2800 / 200)

df_freq = FreqAbs.abstract_frequency(df_freq, ["acc_y"], ws, fs)

# Visualizing Results

subset = df_freq[df_freq["set"] == 15]
subset[["acc_y"]].plot()
subset[['acc_y_max_freq', 'acc_y_freq_weighted', 'acc_y_pse',
       'acc_y_freq_0.0_Hz_ws_14', 'acc_y_freq_0.357_Hz_ws_14',
       'acc_y_freq_0.714_Hz_ws_14', 'acc_y_freq_1.071_Hz_ws_14',
       'acc_y_freq_1.429_Hz_ws_14', 'acc_y_freq_1.786_Hz_ws_14',
       'acc_y_freq_2.143_Hz_ws_14', 'acc_y_freq_2.5_Hz_ws_14',
    ]].plot()

df_freq_list = []
for s in df_freq["set"].unique():
    print(f"Applying Fourier Transformations to Set {s}")
    subset = df_freq[df_freq["set"] == s].reset_index(drop=True).copy()
    subset = FreqAbs.abstract_frequency(subset, predictor_columns, ws, fs)
    df_freq_list.append(subset)
    
df_freq = pd.concat(df_freq_list).set_index("epoch (ms)", drop=True)


# --------------------------------------------------------------
# Dealing with overlapping windows
# --------------------------------------------------------------

df_freq = df_freq.dropna()

# ILOC looks for [ROWS, COLUMNS] snytax
# .iloc[::2] this means we want every second row
# .iloc[::4] this means we want every 4th row

df_freq.iloc[:,:]


# Reducing over fitting of the model. Now we want to limit the data. We are doing this because we have an amount of data that exceeds the needed parameters of what is need for a proper measurement/collection. 
# This step is skip able if the amount of data collected is limited (ie. a small amount of data was collected), or if we want to show every single data point (high precision)
# .iloc[::2] this means we want every second row
df_freq.iloc[::2]

df_freq = df_freq.iloc[::2]

# --------------------------------------------------------------
# Clustering
# --------------------------------------------------------------

# We will be preforming a K-means Clustering as a type of unsupervised machine learning algorithm to group data into a cluster dased on similarities. 

df_cluster = df_freq.copy()

cluster_columns = ["acc_x", "acc_y", "acc_z"]
k_values = range(2, 10)
inertias = []

subset_Test = df_cluster[cluster_columns]

for k in k_values:
    subset = df_cluster[cluster_columns]
    kmeans = KMeans( n_clusters=k, n_init=20, random_state=0)
    cluster_labels = kmeans.fit_predict(subset)
    inertias.append(kmeans.inertia_)

plt.figure(figsize=(10, 10))
plt.plot(k_values, inertias)
plt.xlabel("k")
plt.ylabel("Sum of Squared Distances")
plt.show()

# After plotting we see the elbow at k=4 or k=5. We will use k=5 as it is a lower and more dramatic elbow point
kmeans = KMeans( n_clusters=5, n_init=20, random_state=0)
subset = df_cluster[cluster_columns]
df_cluster["cluster"] = kmeans.fit_predict(subset)


# 3D Plot of the Clusters
fig = plt.figure(figsize=(15, 15))
ax = fig.add_subplot(projection="3d")
for c in df_cluster["cluster"].unique():
    subset = df_cluster[df_cluster["cluster"] == c]
    ax.scatter(subset["acc_x"], subset["acc_y"], subset["acc_z"], label=c)
ax.set_xlabel("X-Axis")
ax.set_ylabel("Y-Axis")
ax.set_zlabel("Z-Axis")
plt.legend()
plt.show()



#  ACC Cluster in Exercises
fig = plt.figure(figsize=(15, 15))
ax = fig.add_subplot(projection="3d")
for l in df_cluster["label"].unique():
    subset = df_cluster[df_cluster["label"] == l]
    ax.scatter(subset["acc_x"], subset["acc_y"], subset["acc_z"], label=l)
ax.set_xlabel("X-Axis")
ax.set_ylabel("Y-Axis")
ax.set_zlabel("Z-Axis")
plt.legend()
plt.show()

# GYR Cluster
fig = plt.figure(figsize=(15, 15))
ax = fig.add_subplot(projection="3d")
for l in df_cluster["label"].unique():
    subset = df_cluster[df_cluster["label"] == l]
    ax.scatter(subset["gyr_x"], subset["gyr_y"], subset["gyr_z"], label=l)
ax.set_xlabel("X-Axis")
ax.set_ylabel("Y-Axis")
ax.set_zlabel("Z-Axis")
plt.legend()
plt.show()


# --------------------------------------------------------------
# Export dataset
# --------------------------------------------------------------

df_cluster.to_pickle("../../data/interim/03_data_features.pkl")