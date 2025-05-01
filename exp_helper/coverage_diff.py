import os
import sys
import matplotlib.pyplot as plt
from matplotlib_venn import venn3

if len(sys.argv) != 2:
    exit()

log_dir = sys.argv[1]

browser_names = ["chromium", "webkit", "firefox"]
# browser_names = ["webkit"]

res = {"minerva": {"chromium": set(), "webkit": set(), "firefox": set()},
       "domato": {"chromium": set(), "webkit": set(), "firefox": set()},
       # "freedom": {"chromium": set(), "webkit": set(), "firefox": set()}
       }

for path in os.listdir(log_dir):
    index = path.find("sancov")
    if index == -1:
        continue
    names = path.split("-")[:-1]
    name = names[1]
    browser_name = names[2]
    if name not in res or browser_name not in browser_names:
        continue
    if name == "favocado" and browser_name == "firefox":
        continue
    cov_path = "-".join(names) + "-cov.cov"
    file = os.path.join(log_dir, path, cov_path)
    with open(file, "rb") as f:
        tmp = set()
        i = 0
        byte = f.read(1)
        a = int.from_bytes(byte, "big")
        if a != 0:
            tmp.add(i)
        while byte:
            byte = f.read(1)
            i += 1
            a = int.from_bytes(byte, "big")
            if a != 0:
                tmp.add(i)
        for not_zero_position in tmp:
            res[name][browser_name].add(not_zero_position)

for browser_name in browser_names:
    l = len(res["minerva"][browser_name])
    m_d_diff = len(res["minerva"][browser_name] - res["domato"][browser_name])
    d_m_diff = len(res["domato"][browser_name] - res["minerva"][browser_name])
    print(f"{browser_name}: {m_d_diff} ({m_d_diff / l}), {d_m_diff} ({d_m_diff / l}), {l}")

#
# for browser_name in browser_names:
#     plt_data = []
#     tool_names = []
#     for tool_name in res.keys():
#         if tool_name == "favocado" and browser_name == "firefox":
#             continue
#         tool_names.append(tool_name)
#         plt_data.append(res[tool_name][browser_name])
#     g = venn3(subsets=plt_data, set_labels=tool_names, set_colors=('darkgrey', 'orange', 'b'))
#     figure_fig = plt.gcf()  # 'get current figure'
#     figure_fig.savefig('cov_diff.pdf',
#                        format='pdf',
#                        dpi=1000,
#                        bbox_inches='tight',
#                        pad_inches=0)
#     break
