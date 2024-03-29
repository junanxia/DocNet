# DocNet
基于PaddlePaddle框架下的通用文档识别系统。

## 系统安装
```
cd app
pip install -r requirement.txt


# 单线程
python server.py

# 多线程
waitress-serve --port=9990 --threads=6 --call server:create_app
```

## 模型训练
```

```