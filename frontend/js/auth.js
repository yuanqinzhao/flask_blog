// 认证相关功能
class Auth {
    // 注册
    static async register(username, email, password) {
        try {
            const data = await APIUtils.request('/register', {
                method: 'POST',
                body: JSON.stringify({ username, email, password })
            });

            // 保存令牌和用户信息
            APIUtils.setTokens(data.access_token, data.refresh_token);
            APIUtils.setUserInfo(data.user);

            return { success: true, data };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    // 登录
    static async login(username, password, remember = false) {
        try {
            const data = await APIUtils.request('/login', {
                method: 'POST',
                body: JSON.stringify({ username, password, remember })
            });

            // 保存令牌和用户信息
            APIUtils.setTokens(data.access_token, data.refresh_token);
            APIUtils.setUserInfo(data.user);

            return { success: true, data };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    // 登出
    static logout() {
        APIUtils.clearTokens();
        window.location.href = '/index.html';
    }

    // 获取当前用户信息
    static async getCurrentUser() {
        try {
            const data = await APIUtils.request('/user/profile');
            APIUtils.setUserInfo(data.user);
            return { success: true, user: data.user };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    // 更新导航栏
    static updateNavbar() {
        const userInfo = APIUtils.getUserInfo();
        const navLinks = document.getElementById('navLinks');

        if (!navLinks) return;

        if (userInfo) {
            navLinks.innerHTML = `
                <a href="/index.html">首页</a>
                <a href="/create_post.html">写文章</a>
                <a href="/user_posts.html?user_id=${userInfo.id}">我的文章</a>
                <a href="#" onclick="Auth.logout()">登出 (${APIUtils.escapeHtml(userInfo.username)})</a>
            `;
        } else {
            navLinks.innerHTML = `
                <a href="/index.html">首页</a>
                <a href="/login.html">登录</a>
                <a href="/register.html">注册</a>
            `;
        }
    }
}