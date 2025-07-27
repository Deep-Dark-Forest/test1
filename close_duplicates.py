import os
import requests
import time

# 配置参数
TOKEN = os.environ['GITHUB_TOKEN']  # 从环境变量获取 token
REPO_OWNER = "Deep-Dark-Forest"
REPO_NAME = "test2"
GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"
DUPLICATE_LABEL = "重复"  # 修改为中文标签

# 查询符合条件的 issue
def fetch_issues(cursor=None):
    query = """
    query ($owner: String!, $name: String!, $cursor: String) {
      repository(owner: $owner, name: $name) {
        issues(
          first: 100,
          states: CLOSED,
          filterBy: {stateReason: NOT_PLANNED},
          after: $cursor
        ) {
          nodes {
            id
            number
            title
            stateReason
            labels(first: 10) {
              nodes { name }
            }
          }
          pageInfo {
            endCursor
            hasNextPage
          }
        }
      }
    }
    """
    variables = {"owner": REPO_OWNER, "name": REPO_NAME, "cursor": cursor}
    response = make_request(query, variables)
    return response.json()["data"]["repository"]["issues"]

# 检查是否包含"重复"标签
def has_duplicate_label(issue):
    labels = [label["name"] for label in issue["labels"]["nodes"]]
    return DUPLICATE_LABEL in labels

# 更新 issue 状态理由
def mark_as_duplicate(issue_id):
    mutation = """
    mutation ($input: UpdateIssueInput!) {
      updateIssue(input: $input) {
        issue { id }
      }
    }
    """
    variables = {"input": {"id": issue_id, "stateReason": "DUPLICATED"}}
    response = make_request(mutation, variables)
    return response

# 发送 GraphQL 请求
def make_request(query, variables):
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {"query": query, "variables": variables}
    response = requests.post(GITHUB_GRAPHQL_URL, json=payload, headers=headers)
    if response.status_code != 200:
        raise Exception(f"请求失败: {response.text}")
    return response

# 主逻辑
def main():
    cursor = None
    has_next_page = True
    
    while has_next_page:
        data = fetch_issues(cursor)
        issues = data["nodes"]
        page_info = data["pageInfo"]
        has_next_page = page_info["hasNextPage"]
        cursor = page_info["endCursor"]

        for issue in issues:
            if issue["stateReason"] == "NOT_PLANNED" and has_duplicate_label(issue):
                print(f"处理 issue #{issue['number']}: {issue['title']}")
                mark_as_duplicate(issue["id"])
                print(f"已标记为重复关闭")
                time.sleep(1)
        
        if has_next_page:
            time.sleep(2)

if __name__ == "__main__":
    main()
