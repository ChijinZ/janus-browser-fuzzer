This markdown is used to illustrate how to get the code and binary of firefox

### Code

Firefox 使用 mercurial 作为版本管理，使用pip按住此工具。 

```
pip install mercurial
```

Firefox 有三个仓库管理代码，为 [mozilla-central](https://hg.mozilla.org/mozilla-central/)， mozilla-beta和[mozilla-release](https://hg.mozilla.org/releases/mozilla-release/)，三个路径分别发布Firefox的nightly，beta和release版。其中central可以直接使用命令```clone https://hg.mozilla.org/mozilla-central/``` 进行下载，release可以使用```hg clone https://hg.mozilla.org/releases/mozilla-release/```下载。或者可以下载unified版本，使用命令```hg clone --uncompressed https://hg.mozilla.org/mozilla-unified```下载unified版本，再使用```hg up release```进入release版本。

### binary

Firefox提供一个python工具下载对应版本的asan build，firefox似乎编译了非常多不一样的版本，不光插桩asan，还提供插桩有覆盖率收集的二进制，十分方便。使用```pip install fuzzfetch```安装工具，使用

```bash
python -m fuzzfetch --asan -n firefox-asan --os Linux --fuzzing --build feceab03c6ff8b7ce7e52e759ddb6a23b310a9e5 --release
```

--asan代表需要asan, -n是下载后的名称，--fuzzing不知道多添加了什么功能。--build后面跟对应commit号或者日期可以下载指定版本的build（比谷歌好）。--release代表从mozilla-release仓库寻找。

参考：

https://github.com/MozillaSecurity/fuzzfetch

https://firefox-source-docs.mozilla.org/tools/sanitizer/asan.html

### webdriver

https://github.com/mozilla/geckodriver 直接下载相应的webdriver