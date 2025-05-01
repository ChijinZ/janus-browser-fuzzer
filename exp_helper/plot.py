import seaborn as sns
import os
import sys
import json
import pandas as pd
import matplotlib.pyplot as plt
import random

if len(sys.argv) != 2:
    exit()

log_dir = sys.argv[1]
sub_title = ["WebKitGTK", "FireFox", "Chromium"]
fuzzer_names = {"domato": "Domato", "freedom": "FreeDom", "favocado": "Favocado",
                "minerva": "Minerva"}
fuzzer_color = {"Domato": "g", "Minerva": "r", "Favocado": "c", "FreeDom": "m"}
plot_data_all = {"webkit": [], "firefox": [], "chromium": []}
for path in os.listdir(log_dir):
    index = path.find("sancov")
    if index == -1:
        continue
    names = path.split("-")[:-1]
    name = names[1]
    browser_name = names[2]
    cov_path = "-".join(names) + "-cov"
    file = os.path.join(log_dir, path, cov_path)
    if name == "favocado" and browser_name == "firefox":
        continue
    print(file)
    start_time = 0
    with open(file) as f:
        res = []
        for line in f.readlines():
            data = json.loads(line)
            if start_time == 0:
                start_time = int(data["timestamp"])
            res.append(
                [int(data["timestamp"]) - start_time,
                 int(data["covered_num"]), fuzzer_names[name]])
        res.append([86400, res[-1][1], res[-1][2]])
        tmp = []
        last_time = 0
        for var in res:
            if var[0] >= last_time:
                tmp.append([last_time / 3600, var[1], var[2]])
                last_time += 3600
        for i in range(len(tmp), 25):
            t = i
            x = tmp[-1]
            tmp.append([t, x[1], x[2]])

        for var in tmp:
            plot_data_all[browser_name].append(var)

fig, axes = plt.subplots(1, 3, figsize=(18, 3))

# plt.xlabel("time (h)", fontsize=10)
# plt.ylabel("edge coverage", fontsize=10)
i = 0
# plt.subplots_adjust(hspace=0.4)
for key, plot_data in plot_data_all.items():
    print(key, len(plot_data))
    df = pd.DataFrame(plot_data, columns=['time (h)', 'edge coverage', 'fuzzer'], dtype=int)
    axes[i].set_title(sub_title[i])

    # print(df.head(5))
    g = sns.lineplot(
        data=df
        , x="time (h)", y="edge coverage", hue="fuzzer", ci=95, ax=axes[i], err_style="band",
        palette=fuzzer_color, hue_order=["Minerva", "Domato", "Favocado", "FreeDom"]
        , markers=False, style_order=["Minerva", "Domato", "Favocado", "FreeDom"], style="fuzzer"
        # , markersize=10, markers=True
    )
    g.legend_.set_title(None)
    g.set_xlabel("time (h)", fontsize=14)
    g.set_ylabel("edge coverage", fontsize=14)
    i += 1
plt.subplots_adjust(wspace=0.3)
figure_fig = plt.gcf()  # 'get current figure'
figure_fig.savefig('plot.pdf',
                   format='pdf',
                   dpi=1000,
                   bbox_inches='tight',
                   pad_inches=0)
