# Easyyibiao
物体检测离线标注工具


## 描述  
该项目基于labelme进行二次开发，主要实现功能为将标注数据一键导出到EasyData平台，目前支持物体检测.  


## 使用方法   
### 方法一   
使用Python启动该项目
```bash
# 1. 安装Python，建议安装Python3.6，安装方式可参考官网：
https://www.python.org/downloads/
# 2. 下载项目(如果直接下载ZIP压缩包，则文件夹名为Easyyibiao-main，第3步改为cd Easyyibiao-main即可)
git clone https://github.com/Baidu-AIP/Easyyibiao.git
# 3. 根据`requirements.txt`安装环境依赖
cd Easyyibiao  
pip3 install -r requirements.txt
# 4. 启动项目
python3 main.py
```

### 方法二
安装独立可执行应用程序
#### MacOS
```bash
# 1. 下载Mac版本压缩包
https://github.com/Baidu-AIP/Easyyibiao/releases
# 2. 解压
tar -zxvf Easyyibiao.tar.gz
# 3. 启动项目
双击Easyyibiao目录下main文件即可运行
```

注： Mac不同版本系统会有不兼容问题，故Mac系统推荐Python启动方式
#### Windows
```bash
# 1. 下载Windows版本压缩包
https://github.com/Baidu-AIP/Easyyibiao/releases
# 2. 解压
Windows下zip解压工具解压即可
# 3. 启动项目
双击Easyyibiao目录下main.exe文件即可运行
```


## 说明
* 数据导出时，会遍历所选文件夹下所有已标图片，可以选择增量导出或全量导出
* 全量上传：将所选文件夹下所有已标图片及标注信息全量导出
* 增量导出：只导出在上一次导出后有过修改的数据


```bash
@misc{labelme2016,
  author =       {Kentaro Wada},
  title =        {{labelme: Image Polygonal Annotation with Python}},
  howpublished = {\url{https://github.com/wkentaro/labelme}},
  year =         {2016}
}
```
