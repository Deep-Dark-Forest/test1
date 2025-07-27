import os
import requests
import time
import json

# 配置参数
TOKEN = os.environ['GITHUB_TOKEN']  # 使用标准环境变量名
REPO_OWNER = "Deep-Dark-Forest"
REPO_NAME = "test2"
GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"
DUPLICATE_LABEL = "重复"

def fetch_issues(cursor=None):
    query = """
    query ($owner: String!, $name: String!, $cursor: String) {
      repository(owner: $owner, name: $name) {
        issues(
          first: 100
          states: CLOSED
          after: $cursor
        ) {
          nodes {
            id
            number
            title
            stateReason
            labels(first: 10) {
              nodes {
                name
              }
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
    return make_request(query, variables)

def has_duplicate_label(issue):
    labels = [label["name"] for label in issue["labels"]["nodes"]]
    return DUPLICATE_LABEL in labels

def mark_as_duplicate(issue_id):
    mutation = """
    mutation ($input: UpdateIssueInput!) {
      updateIssue(input: $input) {
        issue {
          id
        }
      }
    }
    """
    variables = {"input": {"id": issue_id, "stateReason": "DUPLICATED"}}
    return make_request(mutation, variables)

def make_request(query, variables):
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/vnd.github.v4.idl"  # 明确API版本
    }
    payload = {"query": query, "variables": variables}
    
    try:
        response = requests.post(GITHUB_GRAPHQL_URL, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        
        # 调试输出
        print("GraphQL 响应状态:", response.status_code)
        print("GraphQL 响应内容:", json.dumps(result, indent=2))
        
        if "errors" in result:
            raise Exception(f"GraphQL 错误: {result['errors']}")
        if "data" not in result:
            raise Exception("响应中缺少 'data' 字段")
            
        return result
    except Exception as e:
        print(f"请求失败: {str(e)}")
        print("请求负载:", json.dumps(payload, indent=2))
        raise

def main():
    cursor = None
    has_next_page = True
    processed_count = 0
    
    print(f"开始处理仓库: {REPO_OWNER}/{REPO_NAME}")
    print(f"目标标签: '{DUPLICATE_LABEL}'")
    
    while has_next_page:
        print(f"获取页面 (cursor: {cursor})...")
        result = fetch_issues(cursor)
        issues_data = result["data"]["repository"]["issues"]
        issues = issues_data["nodes"]
        page_info = issues_data["pageInfo"]
        has_next_page = page_info["hasNextPage"]
        cursor = page_info["endCursor"]
        
        print(f"本页获取 {len(issues)} 个 issue")
        
        for issue in issues:
            if issue.get("stateReason") == "NOT_PLANNED" and has_duplicate_label(issue):
                print(f"处理 #{issue['number']}: {issue['title']}")
                mark_as_duplicate(issue["id"])
                processed_count += 1
                print(f"已标记为重复关闭 (总计: {processed_count})")
                time.sleep(1)
        
        if has_next_page:
            print("获取下一页...")
            time.sleep(2)
    
    print(f"处理完成! 共标记 {processed_count} 个 issue")

if __name__ == "__main__":
    main()
