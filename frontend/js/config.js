// API配置
const CONFIG = {
    // API基础URL - 修改为你的后端服务器地址
    API_BASE_URL: 'http://192.168.31.66:5000/api',

    // 请求超时时间（毫秒）
    TIMEOUT: 30000,

    // 存储键名
    STORAGE_KEYS: {
        ACCESS_TOKEN: 'access_token',
        REFRESH_TOKEN: 'refresh_token',
        USER_INFO: 'user_info'
    }
};

// 根据环境自动切换API地址
if (window.location.hostname !== '192.168.31.66' && window.location.hostname !== '127.0.0.1') {
    // 生产环境 - 修改为你的后端服务器地址
    CONFIG.API_BASE_URL = 'https://192.168.31.66:5000/api';
}