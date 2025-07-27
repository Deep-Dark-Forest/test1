import os
import requests
import time
import json

# 配置参数
TOKEN = os.environ['GITHUB_TOKEN']  # 使用环境变量中的 token
REPO_OWNER = "Meloong-Git"
REPO_NAME = "PCL"
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

def mark_as_duplicate(issue_id, issue_number):
    """使用 REST API 标记 issue 为重复"""
    rest_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues/{issue_number}"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    data = {
        "state": "closed",
        "state_reason": "duplicate"
    }
    
    print(f"使用 REST API 更新 issue #{issue_number}...")
    response = requests.patch(rest_url, json=data, headers=headers)
    
    if response.status_code == 200:
        print(f"成功标记 issue #{issue_number} 为重复")
        return True
    else:
        print(f"更新失败: {response.status_code} - {response.text}")
        return False

def make_request(query, variables):
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/vnd.github.v4.idl"
    }
    payload = {"query": query, "variables": variables}
    
    try:
        response = requests.post(GITHUB_GRAPHQL_URL, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        
        # 调试输出
        print("GraphQL 响应状态:", response.status_code)
        
        if "errors" in result:
            raise Exception(f"GraphQL 错误: {json.dumps(result['errors'], indent=2)}")
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
    skipped_count = 0
    
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
            # 跳过非 NOT_PLANNED 状态的 issue
            if issue.get("stateReason") != "NOT_PLANNED":
                skipped_count += 1
                continue
                
            if has_duplicate_label(issue):
                print(f"处理 #{issue['number']}: {issue['title']}")
                success = mark_as_duplicate(issue["id"], issue["number"])
                if success:
                    processed_count += 1
                time.sleep(1)  # 避免速率限制
            else:
                skipped_count += 1
        
        if has_next_page:
            print("获取下一页...")
            time.sleep(2)  # 分页请求间暂停
    
    print(f"处理完成! 共标记 {processed_count} 个 issue, 跳过 {skipped_count} 个")

if __name__ == "__main__":
    main()
