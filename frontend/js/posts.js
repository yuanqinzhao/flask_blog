// 文章相关功能
class Posts {
    // 获取文章列表
    static async getPosts(page = 1, userId = null) {
        try {
            let url = `/posts?page=${page}`;
            if (userId) url += `&user_id=${userId}`;

            const data = await APIUtils.request(url);
            return { success: true, ...data };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    // 获取单篇文章
    static async getPost(postId) {
        try {
            const data = await APIUtils.request(`/posts/${postId}`);
            return { success: true, post: data.post };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    // 创建文章
    static async createPost(title, content) {
        try {
            const data = await APIUtils.request('/posts', {
                method: 'POST',
                body: JSON.stringify({ title, content })
            });
            return { success: true, post: data.post };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    // 更新文章
    static async updatePost(postId, title, content) {
        try {
            const data = await APIUtils.request(`/posts/${postId}`, {
                method: 'PUT',
                body: JSON.stringify({ title, content })
            });
            return { success: true, post: data.post };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    // 删除文章
    static async deletePost(postId) {
        try {
            await APIUtils.request(`/posts/${postId}`, {
                method: 'DELETE'
            });
            return { success: true };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    // 渲染文章列表
    static renderPostList(posts, containerId = 'postsContainer') {
        const container = document.getElementById(containerId);
        if (!container) return;

        if (!posts || posts.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-pen-fancy"></i>
                    <h3>还没有文章</h3>
                    ${APIUtils.isAuthenticated() ?
                        '<a href="/create_post.html" class="btn btn-primary">写文章</a>' :
                        '<a href="/login.html" class="btn btn-primary">登录后写作</a>'
                    }
                </div>
            `;
            return;
        }

        container.innerHTML = posts.map(post => `
            <article class="post-card">
                <h2 class="post-title">
                    <a href="/post.html?id=${post.id}">${APIUtils.escapeHtml(post.title)}</a>
                </h2>
                <div class="post-meta">
                    <span class="post-author">
                        <i class="fas fa-user"></i>
                        <a href="/user_posts.html?user_id=${post.user_id}">
                            ${APIUtils.escapeHtml(post.author.username)}
                        </a>
                    </span>
                    <span class="post-date">
                        <i class="fas fa-calendar"></i>
                        ${APIUtils.formatDate(post.created_at)}
                    </span>
                </div>
                <div class="post-excerpt">
                    ${APIUtils.escapeHtml(APIUtils.truncateText(post.content))}
                </div>
                <a href="/post.html?id=${post.id}" class="read-more">
                    阅读更多 →
                </a>
            </article>
        `).join('');
    }
}