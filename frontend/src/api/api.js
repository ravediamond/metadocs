const BASE_URL = process.env.REACT_APP_BACKEND_URL;

// Auth endpoints
export const auth = {
  login: async (email, password) => {
    const response = await fetch(`${BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    if (!response.ok) throw new Error('Login failed');
    return response.json();
  },

  register: async (email, password, name) => {
    const response = await fetch(`${BASE_URL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, name })
    });
    if (!response.ok) throw new Error('Registration failed');
    return response.json();
  }
};

// Domain endpoints
export const domains = {
  create: async (tenantId, domainData, token) => {
    const response = await fetch(`${BASE_URL}/domains/tenants/${tenantId}/domains`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(domainData)
    });
    if (!response.ok) throw new Error('Failed to create domain');
    return response.json();
  },

  getAll: async (tenantId, token) => {
    const response = await fetch(`${BASE_URL}/domains/tenants/${tenantId}/domains`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!response.ok) throw new Error('Failed to fetch domains');
    return response.json();
  },

  getById: async (tenantId, domainId, token) => {
    const response = await fetch(`${BASE_URL}/domains/tenants/${tenantId}/domains/${domainId}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!response.ok) throw new Error('Failed to fetch domain');
    return response.json();
  },

  update: async (tenantId, domainId, domainUpdate, token) => {
    const response = await fetch(`${BASE_URL}/domains/tenants/${tenantId}/domains/${domainId}`, {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(domainUpdate)
    });
    if (!response.ok) throw new Error('Failed to update domain');
    return response.json();
  },

  delete: async (tenantId, domainId, token) => {
    const response = await fetch(`${BASE_URL}/domains/tenants/${tenantId}/domains/${domainId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!response.ok) throw new Error('Failed to delete domain');
    return response.json();
  },

  getData: async (tenantId, domainId, version, token) => {
    const versionQuery = version ? `?version=${version}` : '';
    const response = await fetch(`${BASE_URL}/domains/tenants/${tenantId}/domains/${domainId}/data${versionQuery}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!response.ok) throw new Error('Failed to fetch domain data');
    return response.json();
  },

  getVersions: async (tenantId, domainId, token) => {
    const response = await fetch(`${BASE_URL}/domains/tenants/${tenantId}/domains/${domainId}/versions`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!response.ok) throw new Error('Failed to fetch domain versions');
    return response.json();
  },

  getVersion: async (tenantId, domainId, version, token) => {
    const response = await fetch(`${BASE_URL}/domains/tenants/${tenantId}/domains/${domainId}/versions/${version}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!response.ok) throw new Error('Failed to fetch domain version');
    return response.json();
  },

  createVersion: async (tenantId, domainId, token) => {
    const response = await fetch(`${BASE_URL}/domains/tenants/${tenantId}/domains/${domainId}/versions`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!response.ok) throw new Error('Failed to create domain version');
    return response.json();
  },

  addFilesToVersion: async (tenantId, domainId, version, fileVersions, token) => {
    const response = await fetch(`${BASE_URL}/domains/tenants/${tenantId}/domains/${domainId}/versions/${version}/files`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(fileVersions)
    });
    if (!response.ok) throw new Error('Failed to add files to version');
    return response.json();
  },

  removeFileFromVersion: async (tenantId, domainId, version, fileVersionId, token) => {
    const response = await fetch(`${BASE_URL}/domains/tenants/${tenantId}/domains/${domainId}/versions/${version}/files/${fileVersionId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!response.ok) throw new Error('Failed to remove file from version');
    return response.json();
  },

  getDomainVersionFile: async (tenantId, domainId, version, fileVersionId, token) => {
    const response = await fetch(
      `${BASE_URL}/domains/tenants/${tenantId}/domains/${domainId}/versions/${version}/files/${fileVersionId}`,
      { headers: { 'Authorization': `Bearer ${token}` } }
    );
    if (!response.ok) throw new Error('Failed to fetch domain version file');
    return response.json();
  },

  getDomainVersionFiles: async (tenantId, domainId, version, token) => {
    const response = await fetch(`${BASE_URL}/domains/tenants/${tenantId}/domains/${domainId}/versions/${version}/files`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!response.ok) throw new Error('Failed to fetch domain version files');
    return response.json();
  },
};

// File endpoints
export const files = {
  upload: async (tenantId, domainId, file, description, token) => {
    const formData = new FormData();
    formData.append('uploaded_file', file);
    formData.append('description', description);

    const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/files/tenants/${tenantId}/domains/${domainId}/upload`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`
      },
      body: formData
    });
    if (!response.ok) throw new Error('Failed to upload file');
    return response.json();
  },

  getAll: async (tenantId, domainId, token) => {
    const response = await fetch(`${BASE_URL}/files/tenants/${tenantId}/domains/${domainId}/files`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!response.ok) throw new Error('Failed to fetch files');
    return response.json();
  },

  delete: async (tenantId, domainId, fileId, token) => {
    const response = await fetch(`${BASE_URL}/files/tenants/${tenantId}/domains/${domainId}/files/${fileId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!response.ok) throw new Error('Failed to delete file');
    return response.json();
  }
};

// Processing endpoints
export const processing = {
  getPipeline: async (tenantId, domainId, pipelineId, token) => {
    const response = await fetch(
      `${BASE_URL}/process/tenants/${tenantId}/domains/${domainId}/pipeline/${pipelineId}`,
      {
        headers: { 'Authorization': `Bearer ${token}` }
      }
    );
    if (!response.ok) throw new Error('Failed to fetch pipeline');
    return response.json();
  },

  getProcessingContent: async (tenantId, domainId, pipelineId, versionId, token) => {
    const response = await fetch(
      `${BASE_URL}/process/tenants/${tenantId}/domains/${domainId}/pipeline/${pipelineId}/content/${versionId}`,
      {
        headers: { 'Authorization': `Bearer ${token}` }
      }
    );
    if (!response.ok) throw new Error('Failed to fetch processing content');
    return response.json();
  }
};

// User endpoints
export const users = {
  me: async (token) => {
    const response = await fetch(`${BASE_URL}/users/me`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!response.ok) throw new Error('Failed to fetch user info');
    return response.json();
  },

  getDomainsForUser: async (tenantId, userId, token) => {
    const response = await fetch(`${BASE_URL}/users/tenants/${tenantId}/users/${userId}/domains`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!response.ok) throw new Error('Failed to fetch user domains');
    return response.json();
  },

  getUserRoles: async (tenantId, userId, token) => {
    const response = await fetch(`${BASE_URL}/users/tenants/${tenantId}/users/${userId}/roles`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!response.ok) throw new Error('Failed to fetch user roles');
    return response.json();
  },

  listUsers: async (tenantId, token) => {
    const response = await fetch(`${BASE_URL}/users/tenants/${tenantId}/users`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!response.ok) throw new Error('Failed to fetch users');
    return response.json();
  },

  removeUser: async (tenantId, userId, token) => {
    const response = await fetch(`${BASE_URL}/users/tenants/${tenantId}/users/${userId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!response.ok) throw new Error('Failed to remove user');
    return response.json();
  },

  invite: async (tenantId, invitationData, token) => {
    const response = await fetch(`${BASE_URL}/users/tenants/${tenantId}/invite`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(invitationData)
    });
    if (!response.ok) throw new Error('Failed to create invitation');
    return response.json();
  },

  listInvitations: async (tenantId, token) => {
    const response = await fetch(`${BASE_URL}/users/tenants/${tenantId}/invitations`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!response.ok) throw new Error('Failed to fetch invitations');
    return response.json();
  },

  acceptInvitation: async (invitationId, token) => {
    const response = await fetch(`${BASE_URL}/users/invitations/${invitationId}/accept`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!response.ok) throw new Error('Failed to accept invitation');
    return response.json();
  },

  rejectInvitation: async (invitationId, token) => {
    const response = await fetch(`${BASE_URL}/users/invitations/${invitationId}/reject`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!response.ok) throw new Error('Failed to reject invitation');
    return response.json();
  },

  listDomainUsers: async (tenantId, domainId, token) => {
    const response = await fetch(`${BASE_URL}/users/tenants/${tenantId}/domains/${domainId}/users`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!response.ok) throw new Error('Failed to fetch domain users');
    return response.json();
  }
};

// Config endpoints
export const config = {
  getDomainConfig: async (tenantId, domainId, token) => {
    const response = await fetch(`${BASE_URL}/config/tenants/${tenantId}/domains/${domainId}/config`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!response.ok) throw new Error('Failed to fetch domain config');
    return response.json();
  },

  updateDomainConfig: async (tenantId, domainId, configKey, configValue, token) => {
    const response = await fetch(`${BASE_URL}/config/tenants/${tenantId}/domains/${domainId}/config?config_key=${configKey}&config_value=${configValue}`, {
      method: 'PUT',
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!response.ok) throw new Error('Failed to update domain config');
    return response.json();
  },

  getUserConfig: async (tenantId, userId, token) => {
    const response = await fetch(`${BASE_URL}/config/tenants/${tenantId}/users/${userId}/config`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!response.ok) throw new Error('Failed to fetch user config');
    return response.json();
  },

  updateUserConfig: async (tenantId, userId, configKey, configValue, token) => {
    const response = await fetch(`${BASE_URL}/config/tenants/${tenantId}/users/${userId}/config?config_key=${configKey}&config_value=${configValue}`, {
      method: 'PUT',
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!response.ok) throw new Error('Failed to update user config');
    return response.json();
  },

  getApiKeys: async (token) => {
    const response = await fetch(`${BASE_URL}/config/me/api-keys`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!response.ok) throw new Error('Failed to fetch API keys');
    return response.json();
  },

  createApiKey: async (tenantId, token) => {
    const response = await fetch(`${BASE_URL}/config/tenants/${tenantId}/me/api-keys`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!response.ok) throw new Error('Failed to create API key');
    return response.json();
  },

  revokeApiKey: async (tenantId, apiKeyId, token) => {
    const response = await fetch(`${BASE_URL}/config/tenants/${tenantId}/me/api-keys/${apiKeyId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!response.ok) throw new Error('Failed to revoke API key');
    return response.json();
  }
};


export const roles = {
  getAll: async (tenantId, token) => {
    const response = await fetch(`${BASE_URL}/roles/tenants/${tenantId}/roles`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!response.ok) throw new Error('Failed to fetch roles');
    return response.json();
  },

  assignOrUpdateUserRole: async (tenantId, domainId, userId, roleData, token) => {
    const response = await fetch(`${BASE_URL}/roles/tenants/${tenantId}/domains/${domainId}/users/${userId}/roles`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(roleData)
    });
    if (!response.ok) throw new Error('Failed to assign/update role');
    return response.json();
  },

  revokeUserRole: async (tenantId, domainId, userId, roleName, token) => {
    const response = await fetch(`${BASE_URL}/roles/tenants/${tenantId}/domains/${domainId}/users/${userId}/roles/${roleName}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!response.ok) throw new Error('Failed to revoke role');
    return response.json();
  },

  getUserRoles: async (tenantId, userId, token) => {
    const response = await fetch(`${BASE_URL}/roles/tenants/${tenantId}/users/${userId}/roles`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!response.ok) throw new Error('Failed to fetch user roles');
    return response.json();
  }
};

export const chat = {
  analyzeQuery: async (tenantId, domainId, query, token, versions = {}) => {
    const response = await fetch(
      `${BASE_URL}/chat/tenants/${tenantId}/domains/${domainId}/chat`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          message: { content: query },
          versions: {
            parse_versions: versions.parseVersions || {},
            extract_versions: versions.extractVersions || {},
            merge_version_id: versions.mergeVersionId || null,
            group_version_id: versions.groupVersionId || null,
            ontology_version_id: versions.ontologyVersionId || null
          }
        })
      }
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Failed to analyze query');
    }

    return response.json();
  },

  getTodoList: async (tenantId, domainId, token) => {
    const response = await fetch(
      `${BASE_URL}/chat/tenants/${tenantId}/domains/${domainId}/chat/todo`,
      {
        headers: { 'Authorization': `Bearer ${token}` }
      }
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Failed to fetch todo list');
    }

    return response.json();
  },

  removeTodoItem: async (tenantId, domainId, itemId, token) => {
    const response = await fetch(
      `${BASE_URL}/chat/tenants/${tenantId}/domains/${domainId}/chat/todo/${itemId}`,
      {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      }
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Failed to remove todo item');
    }

    return response.json();
  },

  updateTodoItem: async (tenantId, domainId, itemId, token) => {
    const response = await fetch(
      `${BASE_URL}/chat/tenants/${tenantId}/domains/${domainId}/chat/todo/${itemId}`,
      {
        method: 'PUT',
        headers: { 'Authorization': `Bearer ${token}` }
      }
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Failed to update todo item');
    }

    return response.json();
  }
};