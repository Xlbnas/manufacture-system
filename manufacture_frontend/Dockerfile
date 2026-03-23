# 使用Node.js 18作为基础镜像
FROM node:18-alpine

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY package*.json ./

# 安装依赖
RUN npm install

# 复制项目代码
COPY . .

# 构建生产版本
RUN npm run build

# 安装serve包用于提供静态文件
RUN npm install -g serve

# 暴露3000端口
EXPOSE 3000

# 启动服务
CMD ["serve", "-s", "dist", "-l", "3000"]