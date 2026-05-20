// frontend/js/utils.js
class APIUtils {
    static getAccessToken() {
        return localStorage.getItem(CONFIG.STORAGE_KEYS.ACCESS_TOKEN);
    }

    static getRefreshToken() {
        return localStorage.getItem(CONFIG.STORAGE_KEYS.REFRESH_TOKEN);
    }

    static setTokens(accessToken, refreshToken = null) {
        localStorage.setItem(CONFIG.STORAGE_KEYS.ACCESS_TOKEN, accessToken);
        if (refreshToken) {
            localStorage.setItem(CONFIG.STORAGE_KEYS.REFRESH_TOKEN, refreshToken);
        }
    }

    static clearTokens() {
        localStorage.removeItem(CONFIG.STORAGE_KEYS.ACCESS_TOKEN);
        localStorage.removeItem(CONFIG.STORAGE_KEYS.REFRESH_TOKEN);
        localStorage.removeItem(CONFIG.STORAGE_KEYS.USER_INFO);
    }

    static getUserInfo() {
        const userInfo = localStorage.getItem(CONFIG.STORAGE_KEYS.USER_INFO);
        return userInfo ? JSON.parse(userInfo) : null;
    }

    static setUserInfo(userInfo) {
        localStorage.setItem(CONFIG.STORAGE_KEYS.USER_INFO, JSON.stringify(userInfo));
    }

    // 核心修复：重写request方法，确保Authorization头格式正确
    static async request(url, options = {}) {
        const token = this.getAccessToken();

        // 构建请求配置
        const config = {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                'ngrok-skip-browser-warning': 'true'
                ...options.headers
            }
        };

        // 确保Authorization头格式正确
        if (token) {
            // 关键修复：确保是 "Bearer " + token 的格式
            config.headers['Authorization'] = `Bearer ${token}`;
        }

        try {
            const response = await fetch(`${CONFIG.API_BASE_URL}${url}`, config);

            if (response.status === 401) {
                // Token过期，尝试刷新
                const refreshed = await this.refreshToken();
                if (refreshed) {
                    config.headers['Authorization'] = `Bearer ${this.getAccessToken()}`;
                    const retryResponse = await fetch(`${CONFIG.API_BASE_URL}${url}`, config);
                    return await this.handleResponse(retryResponse);
                }
            }

            return await this.handleResponse(response);
        } catch (error) {
            console.error('请求失败:', error);
            throw error;
        }
    }

    static async handleResponse(response) {
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || data.msg || '请求失败');
        }

        return data;
    }

    static async refreshToken() {
        const refreshToken = this.getRefreshToken();
        if (!refreshToken) {
            this.clearTokens();
            window.location.href = '/login.html';
            return false;
        }

        try {
            const response = await fetch(`${CONFIG.API_BASE_URL}/refresh`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${refreshToken}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                this.setTokens(data.access_token);
                return true;
            }
        } catch (error) {
            console.error('令牌刷新失败:', error);
        }

        this.clearTokens();
        window.location.href = '/login.html';
        return false;
    }

    static isAuthenticated() {
        return !!this.getAccessToken();
    }

    static formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    static escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, char => map[char]);
    }

    static truncateText(text, maxLength = 200) {
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    }
}