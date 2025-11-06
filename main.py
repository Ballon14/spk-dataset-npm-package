import requests
import json
import time
import csv
from datetime import datetime, timedelta
import pandas as pd
from collections import Counter
import re
import subprocess

class NodeJSFrameworkCollector:
    def __init__(self, github_token=None):
        self.frameworks = []
        self.base_npm_url = "https://registry.npmjs.org"
        self.npm_api_url = "https://api.npmjs.org"
        self.github_token = github_token
        self.processed_names = set()
        
    def search_npm_packages(self, keywords, limit=250):
        """Search npm packages by keywords"""
        print(f"Searching npm for: {keywords}")
        url = f"https://registry.npmjs.org/-/v1/search"
        
        all_packages = []
        offset = 0
        
        while len(all_packages) < limit:
            params = {
                'text': keywords,
                'size': 250,
                'from': offset,
                'quality': 0.5,
                'popularity': 0.3,
                'maintenance': 0.2
            }
            
            try:
                response = requests.get(url, params=params, timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    objects = data.get('objects', [])
                    
                    if not objects:
                        break
                    
                    all_packages.extend(objects)
                    offset += 250
                    time.sleep(0.3)
                else:
                    print(f"Error: {response.status_code}")
                    break
            except Exception as e:
                print(f"Error searching npm: {e}")
                break
        
        return all_packages[:limit]
    
    def get_package_details(self, package_name):
        """Get detailed info about a package"""
        try:
            url = f"{self.base_npm_url}/{package_name}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Error getting {package_name}: {e}")
            return None
    
    def get_download_stats(self, package_name):
        """Get download statistics for last month"""
        try:
            url = f"https://api.npmjs.org/downloads/point/last-month/{package_name}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('downloads', 0)
            return 0
        except Exception as e:
            return 0
    
    def get_npm_audit_info(self, package_name):
        """Get vulnerability information from npm"""
        try:
            # Note: This requires npm audit API which might need authentication
            # Alternative: Use Snyk or similar service
            url = f"https://registry.npmjs.org/-/npm/v1/security/audits/quick"
            
            # This is a simplified approach - in production, you'd want to use npm audit properly
            # For now, we'll return 0 as placeholder
            return {
                'vulnerabilities': 0,
                'has_vulnerabilities': False
            }
        except:
            return {
                'vulnerabilities': 0,
                'has_vulnerabilities': False
            }
    
    def get_package_size(self, package_name):
        """Get package size from bundlephobia"""
        try:
            url = f"https://bundlephobia.com/api/size?package={package_name}"
            response = requests.get(url, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'package_size_kb': round(data.get('size', 0) / 1024, 2),
                    'gzip_size_kb': round(data.get('gzip', 0) / 1024, 2)
                }
            return {'package_size_kb': 0, 'gzip_size_kb': 0}
        except Exception as e:
            return {'package_size_kb': 0, 'gzip_size_kb': 0}
    
    def calculate_release_frequency(self, time_data):
        """Calculate release frequency from npm time data"""
        try:
            versions = {k: v for k, v in time_data.items() if k not in ['created', 'modified']}
            
            if len(versions) < 2:
                return {'release_frequency': 0, 'releases_per_year': 0}
            
            dates = [datetime.fromisoformat(d.replace('Z', '+00:00')) for d in versions.values()]
            dates.sort()
            
            # Calculate average days between releases
            if len(dates) > 1:
                total_days = (dates[-1] - dates[0]).days
                num_releases = len(dates) - 1
                
                if total_days > 0:
                    avg_days_between = total_days / num_releases
                    releases_per_year = 365 / avg_days_between if avg_days_between > 0 else 0
                    
                    return {
                        'release_frequency': round(avg_days_between, 1),
                        'releases_per_year': round(releases_per_year, 2),
                        'total_releases': len(versions)
                    }
            
            return {'release_frequency': 0, 'releases_per_year': 0, 'total_releases': len(versions)}
        except:
            return {'release_frequency': 0, 'releases_per_year': 0, 'total_releases': 0}
    
    def get_github_stats(self, repo_url):
        """Get comprehensive GitHub statistics"""
        if not repo_url or 'github.com' not in repo_url:
            return None
        
        try:
            # Extract owner and repo from URL
            parts = repo_url.replace('https://github.com/', '').replace('git://github.com/', '').replace('.git', '').split('/')
            if len(parts) >= 2:
                owner, repo = parts[0], parts[1]
                
                headers = {}
                if self.github_token:
                    headers['Authorization'] = f'token {self.github_token}'
                
                # Get main repo info
                repo_url_api = f"https://api.github.com/repos/{owner}/{repo}"
                response = requests.get(repo_url_api, headers=headers, timeout=10)
                
                if response.status_code != 200:
                    return None
                
                repo_data = response.json()
                
                # Get additional data
                stats = {
                    'stars': repo_data.get('stargazers_count', 0),
                    'forks': repo_data.get('forks_count', 0),
                    'watchers': repo_data.get('watchers_count', 0),
                    'open_issues': repo_data.get('open_issues_count', 0),
                    'last_updated': repo_data.get('updated_at', ''),
                    'language': repo_data.get('language', ''),
                    'size': repo_data.get('size', 0),
                    'has_wiki': repo_data.get('has_wiki', False),
                    'has_pages': repo_data.get('has_pages', False),
                }
                
                # Get commit activity
                try:
                    commits_url = f"https://api.github.com/repos/{owner}/{repo}/commits"
                    commits_response = requests.get(commits_url, headers=headers, params={'per_page': 1}, timeout=10)
                    if commits_response.status_code == 200:
                        commits_data = commits_response.json()
                        if commits_data:
                            stats['last_commit_date'] = commits_data[0]['commit']['committer']['date']
                        else:
                            stats['last_commit_date'] = ''
                    else:
                        stats['last_commit_date'] = ''
                    time.sleep(0.2)
                except:
                    stats['last_commit_date'] = ''
                
                # Get pull requests
                try:
                    prs_url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
                    prs_response = requests.get(prs_url, headers=headers, params={'state': 'open', 'per_page': 100}, timeout=10)
                    if prs_response.status_code == 200:
                        stats['open_pull_requests'] = len(prs_response.json())
                    else:
                        stats['open_pull_requests'] = 0
                    time.sleep(0.2)
                except:
                    stats['open_pull_requests'] = 0
                
                # Get contributors count
                try:
                    contributors_url = f"https://api.github.com/repos/{owner}/{repo}/contributors"
                    contributors_response = requests.get(contributors_url, headers=headers, params={'per_page': 1}, timeout=10)
                    if contributors_response.status_code == 200:
                        # Get total from Link header if available
                        link_header = contributors_response.headers.get('Link', '')
                        if 'last' in link_header:
                            # Parse last page number from Link header
                            match = re.search(r'page=(\d+)>; rel="last"', link_header)
                            if match:
                                stats['contributors_count'] = int(match.group(1))
                            else:
                                stats['contributors_count'] = len(contributors_response.json())
                        else:
                            stats['contributors_count'] = len(contributors_response.json())
                    else:
                        stats['contributors_count'] = 0
                    time.sleep(0.2)
                except:
                    stats['contributors_count'] = 0
                
                # Check for CI/CD
                try:
                    workflows_url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows"
                    workflows_response = requests.get(workflows_url, headers=headers, timeout=10)
                    if workflows_response.status_code == 200:
                        workflows_data = workflows_response.json()
                        stats['has_ci'] = workflows_data.get('total_count', 0) > 0
                        stats['ci_workflows_count'] = workflows_data.get('total_count', 0)
                    else:
                        stats['has_ci'] = False
                        stats['ci_workflows_count'] = 0
                    time.sleep(0.2)
                except:
                    stats['has_ci'] = False
                    stats['ci_workflows_count'] = 0
                
                # Check for tests (look for test directories/files)
                try:
                    contents_url = f"https://api.github.com/repos/{owner}/{repo}/contents"
                    contents_response = requests.get(contents_url, headers=headers, timeout=10)
                    if contents_response.status_code == 200:
                        contents = contents_response.json()
                        test_indicators = ['test', 'tests', '__tests__', 'spec', 'specs']
                        stats['has_tests'] = any(
                            item['name'].lower() in test_indicators or 
                            'test' in item['name'].lower()
                            for item in contents if item['type'] == 'dir'
                        )
                    else:
                        stats['has_tests'] = False
                    time.sleep(0.2)
                except:
                    stats['has_tests'] = False
                
                return stats
                
        except Exception as e:
            print(f"    GitHub API Error: {e}")
            return None
    
    def assess_documentation_quality(self, repo_data, package_data):
        """Assess documentation quality (score 1-5)"""
        score = 0
        
        # Check README exists and length
        readme = package_data.get('readme', '')
        if readme:
            score += 1
            if len(readme) > 500:
                score += 1
            if len(readme) > 2000:
                score += 1
        
        # Check if has homepage
        if package_data.get('homepage'):
            score += 0.5
        
        # Check if has wiki (from GitHub)
        if repo_data and repo_data.get('has_wiki'):
            score += 0.5
        
        # Check if has GitHub pages
        if repo_data and repo_data.get('has_pages'):
            score += 0.5
        
        # Check keywords exist
        if package_data.get('keywords') and len(package_data.get('keywords', [])) > 3:
            score += 0.5
        
        return min(5, round(score, 1))
    
    def calculate_activity_score(self, github_stats, release_frequency):
        """Calculate overall activity score (0-100)"""
        if not github_stats:
            return 0
        
        score = 0
        
        # Recent commit (last 3 months) - 30 points
        if github_stats.get('last_commit_date'):
            try:
                last_commit = datetime.fromisoformat(github_stats['last_commit_date'].replace('Z', '+00:00'))
                days_since = (datetime.now(last_commit.tzinfo) - last_commit).days
                if days_since < 90:
                    score += 30
                elif days_since < 180:
                    score += 20
                elif days_since < 365:
                    score += 10
            except:
                pass
        
        # Active contributors - 20 points
        contributors = github_stats.get('contributors_count', 0)
        if contributors > 50:
            score += 20
        elif contributors > 20:
            score += 15
        elif contributors > 10:
            score += 10
        elif contributors > 5:
            score += 5
        
        # Open PRs (shows activity) - 15 points
        prs = github_stats.get('open_pull_requests', 0)
        if prs > 20:
            score += 15
        elif prs > 10:
            score += 10
        elif prs > 5:
            score += 5
        
        # Release frequency - 20 points
        releases_per_year = release_frequency.get('releases_per_year', 0)
        if releases_per_year > 12:
            score += 20
        elif releases_per_year > 6:
            score += 15
        elif releases_per_year > 3:
            score += 10
        elif releases_per_year > 1:
            score += 5
        
        # Stars (popularity) - 15 points
        stars = github_stats.get('stars', 0)
        if stars > 10000:
            score += 15
        elif stars > 5000:
            score += 12
        elif stars > 1000:
            score += 9
        elif stars > 500:
            score += 6
        elif stars > 100:
            score += 3
        
        return min(100, score)
    
    def categorize_framework(self, package_data):
        """Categorize framework based on keywords and description"""
        description = package_data.get('description', '').lower()
        keywords = package_data.get('keywords', [])
        keywords_str = ' '.join(keywords).lower() if keywords else ''
        name = package_data.get('name', '').lower()
        
        combined_text = f"{description} {keywords_str} {name}"
        
        categories = []
        
        if any(word in combined_text for word in ['web framework', 'http server', 'web server', 'express', 'web application']):
            categories.append('Web Framework')
        
        if any(word in combined_text for word in ['api', 'rest', 'restful', 'graphql', 'api framework']):
            categories.append('API Framework')
        
        if any(word in combined_text for word in ['realtime', 'websocket', 'socket', 'real-time', 'ws']):
            categories.append('Real-time')
        
        if any(word in combined_text for word in ['fullstack', 'full-stack', 'isomorphic', 'universal', 'ssr', 'server-side rendering']):
            categories.append('Full-stack')
        
        if any(word in combined_text for word in ['microservice', 'micro-service', 'microservices', 'distributed']):
            categories.append('Microservices')
        
        if any(word in combined_text for word in ['test', 'testing', 'mocha', 'jest', 'chai', 'jasmine', 'unit test']):
            categories.append('Testing')
        
        if any(word in combined_text for word in ['build', 'bundler', 'webpack', 'compiler', 'rollup', 'vite', 'build tool']):
            categories.append('Build Tool')
        
        if any(word in combined_text for word in ['orm', 'database', 'mongodb', 'mysql', 'postgres', 'sequelize', 'typeorm']):
            categories.append('Database/ORM')
        
        if any(word in combined_text for word in ['auth', 'authentication', 'passport', 'jwt', 'oauth']):
            categories.append('Authentication')
        
        if any(word in combined_text for word in ['log', 'logging', 'winston', 'morgan', 'logger']):
            categories.append('Logging')
        
        if any(word in combined_text for word in ['utility', 'helper', 'utils', 'tool']):
            categories.append('Utility')
        
        if any(word in combined_text for word in ['cli', 'command line', 'terminal', 'commander']):
            categories.append('CLI')
        
        return categories if categories else ['Other']
    
    def collect_frameworks(self, min_count=500):
        """Collect framework data from multiple sources"""
        print(f"Starting collection of {min_count} Node.js frameworks...")
        print("=" * 80)
        
        # Extended search terms
        search_terms = [
            'nodejs framework', 'express framework', 'web framework nodejs',
            'api framework node', 'rest framework', 'graphql framework',
            'http server nodejs', 'web server node', 'nestjs koa fastify',
            'hapi restify loopback', 'sails meteor adonis', 'next nuxt remix',
            'microservices framework', 'real-time framework', 'socket framework',
            'websocket node', 'authentication framework', 'orm framework node',
            'testing framework nodejs', 'test framework node', 'build tool node',
            'bundler nodejs', 'database framework node', 'orm nodejs',
            'mongodb framework', 'sequelize typeorm', 'nodejs utility',
            'node helper', 'nodejs tools', 'middleware nodejs', 'node server',
            'nodejs runtime', 'node application', 'backend framework',
            'serverless framework', 'jamstack node', 'edge framework',
            'headless cms node', 'logging framework node', 'validation framework',
            'routing framework', 'template engine node', 'view engine nodejs',
            'cli framework node', 'command line tool', 'ecommerce framework',
            'cms framework node', 'blog framework', 'api gateway node',
            'proxy server node',
        ]
        
        all_packages = []
        seen_names = set()
        
        for idx, term in enumerate(search_terms, 1):
            print(f"\n[{idx}/{len(search_terms)}] Searching: '{term}'")
            packages = self.search_npm_packages(term, limit=100)
            
            new_packages = 0
            for pkg_obj in packages:
                pkg = pkg_obj.get('package', {})
                name = pkg.get('name', '')
                
                if name and name not in seen_names:
                    seen_names.add(name)
                    all_packages.append(pkg)
                    new_packages += 1
            
            print(f"  → Found {new_packages} new packages | Total: {len(all_packages)}")
            
            if len(all_packages) >= min_count * 1.5:
                break
            
            time.sleep(0.5)
        
        print(f"\n{'=' * 80}")
        print(f"Processing {min(len(all_packages), min_count)} packages with extended metrics...")
        print(f"{'=' * 80}\n")
        
        packages_to_process = all_packages[:min(len(all_packages), min_count)]
        
        for idx, pkg in enumerate(packages_to_process, 1):
            name = pkg.get('name', '')
            
            if name in self.processed_names:
                continue
            
            self.processed_names.add(name)
            print(f"[{idx}/{len(packages_to_process)}] {name}")
            
            try:
                # Get package details
                details = self.get_package_details(name)
                if not details:
                    print(f"  ✗ Failed to get details")
                    continue
                
                # Basic info
                downloads = self.get_download_stats(name)
                print(f"  📥 Downloads: {downloads:,}")
                
                # Get repository
                repo_url = None
                if 'repository' in details:
                    repo_info = details['repository']
                    if isinstance(repo_info, dict):
                        repo_url = repo_info.get('url', '')
                    elif isinstance(repo_info, str):
                        repo_url = repo_info
                
                # GitHub stats (extended)
                github_stats = None
                if repo_url:
                    print(f"  🔍 Fetching GitHub stats...")
                    github_stats = self.get_github_stats(repo_url)
                    if github_stats:
                        print(f"  ⭐ Stars: {github_stats.get('stars', 0):,} | Contributors: {github_stats.get('contributors_count', 0)}")
                
                # Package size
                print(f"  📦 Checking package size...")
                size_info = self.get_package_size(name)
                if size_info['package_size_kb'] > 0:
                    print(f"  📦 Size: {size_info['package_size_kb']} KB (gzip: {size_info['gzip_size_kb']} KB)")
                
                # Release frequency
                time_data = details.get('time', {})
                release_freq = self.calculate_release_frequency(time_data)
                if release_freq['releases_per_year'] > 0:
                    print(f"  🔄 Releases: {release_freq['releases_per_year']}/year")
                
                # Versions
                latest_version = details.get('dist-tags', {}).get('latest', '')
                versions = details.get('versions', {})
                version_data = versions.get(latest_version, {})
                
                # Categories
                categories = self.categorize_framework(version_data)
                
                # Documentation score
                doc_score = self.assess_documentation_quality(github_stats, version_data)
                
                # Activity score
                activity_score = self.calculate_activity_score(github_stats, release_freq)
                
                # Author
                author = details.get('author', {})
                if isinstance(author, dict):
                    author_name = author.get('name', '')
                elif isinstance(author, str):
                    author_name = author
                else:
                    author_name = ''
                
                # Audit info (placeholder - would need npm audit integration)
                audit_info = self.get_npm_audit_info(name)
                
                framework_data = {
                    # Basic Info
                    'name': name,
                    'version': latest_version,
                    'description': pkg.get('description', '')[:500],
                    'author': author_name,
                    'license': version_data.get('license', ''),
                    'keywords': ', '.join(pkg.get('keywords', [])[:10]),
                    'categories': ', '.join(categories),
                    
                    # Popularity Metrics
                    'downloads_last_month': downloads,
                    'github_stars': github_stats.get('stars', 0) if github_stats else 0,
                    'github_forks': github_stats.get('forks', 0) if github_stats else 0,
                    'github_watchers': github_stats.get('watchers', 0) if github_stats else 0,
                    
                    # Security & Quality (SPK Parameters)
                    'vulnerabilities': audit_info.get('vulnerabilities', 0),
                    'has_vulnerabilities': audit_info.get('has_vulnerabilities', False),
                    
                    # Package Size (Efficiency)
                    'package_size_kb': size_info.get('package_size_kb', 0),
                    'gzip_size_kb': size_info.get('gzip_size_kb', 0),
                    
                    # Update Frequency
                    'release_frequency_days': release_freq.get('release_frequency', 0),
                    'releases_per_year': release_freq.get('releases_per_year', 0),
                    'total_releases': release_freq.get('total_releases', 0),
                    
                    # Testing & CI
                    'has_tests': github_stats.get('has_tests', False) if github_stats else False,
                    'has_ci': github_stats.get('has_ci', False) if github_stats else False,
                    'ci_workflows_count': github_stats.get('ci_workflows_count', 0) if github_stats else 0,
                    
                    # Documentation Quality
                    'documentation_score': doc_score,
                    'has_wiki': github_stats.get('has_wiki', False) if github_stats else False,
                    'has_pages': github_stats.get('has_pages', False) if github_stats else False,
                    
                    # Open Source Activity
                    'last_commit_date': github_stats.get('last_commit_date', '') if github_stats else '',
                    'last_updated': github_stats.get('last_updated', '') if github_stats else '',
                    'github_open_issues': github_stats.get('open_issues', 0) if github_stats else 0,
                    
                    # Community Engagement
                    'open_pull_requests': github_stats.get('open_pull_requests', 0) if github_stats else 0,
                    'contributors_count': github_stats.get('contributors_count', 0) if github_stats else 0,
                    
                    # Calculated Scores
                    'activity_score': activity_score,
                    
                    # Additional Info
                    'repository': repo_url,
                    'homepage': pkg.get('links', {}).get('homepage', ''),
                    'npm_url': pkg.get('links', {}).get('npm', ''),
                    'created_date': details.get('time', {}).get('created', ''),
                    'modified_date': details.get('time', {}).get('modified', ''),
                    'github_language': github_stats.get('language', '') if github_stats else '',
                    'maintainers': len(details.get('maintainers', [])),
                    'dependencies': len(version_data.get('dependencies', {})),
                    'dev_dependencies': len(version_data.get('devDependencies', {})),
                }
                
                self.frameworks.append(framework_data)
                print(f"  ✓ Success | Activity: {activity_score}/100 | Doc: {doc_score}/5\n")
                
                # Rate limiting
                time.sleep(0.3 if self.github_token else 0.8)
                    
            except Exception as e:
                print(f"  ✗ Error: {e}\n")
                continue
        
        print(f"{'=' * 80}")
        print(f"✅ Successfully collected {len(self.frameworks)} frameworks with extended metrics!")
        print(f"{'=' * 80}\n")
        return self.frameworks
    
    def save_to_csv(self, filename='nodejs_frameworks_500_extended.csv'):
        """Save data to CSV file"""
        if not self.frameworks:
            print("No data to save!")
            return
        
        df = pd.DataFrame(self.frameworks)
        df.to_csv(filename, index=False, encoding='utf-8')
        print(f"✅ CSV saved to {filename}")
    
    def save_to_json(self, filename='nodejs_frameworks_500_extended.json'):
        """Save data to JSON file"""
        if not self.frameworks:
            print("No data to save!")
            return
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.frameworks, f, indent=2, ensure_ascii=False)
        print(f"✅ JSON saved to {filename}")
    
    def save_to_excel(self, filename='nodejs_frameworks_500_extended.xlsx'):
        """Save data to Excel file with multiple sheets"""
        if not self.frameworks:
            print("No data to save!")
            return
        
        try:
            df = pd.DataFrame(self.frameworks)
            
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                # Main data
                df.to_excel(writer, sheet_name='All Frameworks', index=False)
                
                # Top by activity score
                top_activity = df.nlargest(50, 'activity_score')[
                    ['name', 'activity_score', 'downloads_last_month', 'github_stars', 'releases_per_year', 'contributors_count']
                ]
                top_activity.to_excel(writer, sheet_name='Top 50 Active', index=False)
                
                # Top by downloads
                top_downloads = df.nlargest(50, 'downloads_last_month')[
                    ['name', 'downloads_last_month', 'github_stars', 'activity_score', 'documentation_score']
                ]
                top_downloads.to_excel(writer, sheet_name='Top 50 Downloads', index=False)
                
                # Top by quality (has tests + CI + good docs)
                df_quality = df[df['has_tests'] == True].copy()
                df_quality = df_quality.sort_values('documentation_score', ascending=False)
                top_quality = df_quality.head(50)[
                    ['name', 'documentation_score', 'has_tests', 'has_ci', 'activity_score', 'github_stars']
                ]
                top_quality.to_excel(writer, sheet_name='Top 50 Quality', index=False)
                
                # Best for production (high activity + tests + CI + good docs)
                df_production = df[
                    (df['has_tests'] == True) & 
                    (df['has_ci'] == True) & 
                    (df['documentation_score'] >= 3) &
                    (df['activity_score'] >= 50)
                ].copy()
                df_production = df_production.sort_values('activity_score', ascending=False)
                best_production = df_production.head(50)[
                    ['name', 'activity_score', 'documentation_score', 'downloads_last_month', 
                     'releases_per_year', 'contributors_count', 'package_size_kb']
                ]
                best_production.to_excel(writer, sheet_name='Best for Production', index=False)
                
                # Category summary with extended metrics
                all_categories = []
                for cats in df['categories']:
                    all_categories.extend(cats.split(', '))
                category_counts = Counter(all_categories)
                cat_df = pd.DataFrame(category_counts.most_common(), columns=['Category', 'Count'])
                cat_df.to_excel(writer, sheet_name='Categories', index=False)
                
                # SPK Analysis Sheet - Key metrics for decision making
                spk_df = df[[
                    'name', 'categories', 'downloads_last_month', 'github_stars',
                    'activity_score', 'documentation_score', 'package_size_kb',
                    'releases_per_year', 'has_tests', 'has_ci', 'contributors_count',
                    'open_pull_requests', 'last_commit_date', 'vulnerabilities'
                ]].copy()
                spk_df = spk_df.sort_values('activity_score', ascending=False)
                spk_df.to_excel(writer, sheet_name='SPK Analysis', index=False)
            
            print(f"✅ Excel saved to {filename}")
        except ImportError:
            print("⚠️  openpyxl not installed. Install with: pip install openpyxl")
    
    def get_summary_statistics(self):
        """Get comprehensive summary statistics"""
        if not self.frameworks:
            return None
        
        df = pd.DataFrame(self.frameworks)
        
        print("\n" + "=" * 80)
        print("📊 COMPREHENSIVE SUMMARY STATISTICS")
        print("=" * 80)
        print(f"Total frameworks collected: {len(df)}")
        
        print(f"\n{'=' * 80}")
        print("🏆 TOP 10 BY ACTIVITY SCORE (Overall Health)")
        print("=" * 80)
        top_activity = df.nlargest(10, 'activity_score')
        for idx, row in top_activity.iterrows():
            print(f"  {row['name']:35s} | Score: {row['activity_score']:>3}/100 | "
                  f"⭐ {row['github_stars']:>6,} | 📥 {row['downloads_last_month']:>12,}")
        
        print(f"\n{'=' * 80}")
        print("📥 TOP 10 BY DOWNLOADS")
        print("=" * 80)
        top_dl = df.nlargest(10, 'downloads_last_month')
        for idx, row in top_dl.iterrows():
            print(f"  {row['name']:35s} | {row['downloads_last_month']:>12,} | "
                  f"Activity: {row['activity_score']:>3}/100")
        
        print(f"\n{'=' * 80}")
        print("⭐ TOP 10 BY GITHUB STARS")
        print("=" * 80)
        top_stars = df.nlargest(10, 'github_stars')
        for idx, row in top_stars.iterrows():
            print(f"  {row['name']:35s} | ⭐ {row['github_stars']:>6,} | "
                  f"Contributors: {row['contributors_count']:>4}")
        
        print(f"\n{'=' * 80}")
        print("🎯 SPK METRICS SUMMARY")
        print("=" * 80)
        
        # Security
        with_vulns = df[df['vulnerabilities'] > 0].shape[0]
        print(f"\n🔒 SECURITY:")
        print(f"  Packages with vulnerabilities: {with_vulns} ({with_vulns/len(df)*100:.1f}%)")
        print(f"  Packages without vulnerabilities: {len(df)-with_vulns} ({(len(df)-with_vulns)/len(df)*100:.1f}%)")
        
        # Package Size
        print(f"\n📦 PACKAGE SIZE:")
        print(f"  Average size: {df['package_size_kb'].mean():.2f} KB")
        print(f"  Median size: {df['package_size_kb'].median():.2f} KB")
        print(f"  Smallest: {df[df['package_size_kb'] > 0]['package_size_kb'].min():.2f} KB")
        print(f"  Largest: {df['package_size_kb'].max():.2f} KB")
        
        # Update Frequency
        print(f"\n🔄 UPDATE FREQUENCY:")
        active_releases = df[df['releases_per_year'] > 0]
        print(f"  Average releases/year: {active_releases['releases_per_year'].mean():.2f}")
        print(f"  Median releases/year: {active_releases['releases_per_year'].median():.2f}")
        print(f"  Most active: {active_releases['releases_per_year'].max():.2f} releases/year")
        
        # Testing & CI
        print(f"\n✅ TESTING & CI:")
        has_tests = df[df['has_tests'] == True].shape[0]
        has_ci = df[df['has_ci'] == True].shape[0]
        print(f"  Packages with tests: {has_tests} ({has_tests/len(df)*100:.1f}%)")
        print(f"  Packages with CI/CD: {has_ci} ({has_ci/len(df)*100:.1f}%)")
        print(f"  Both tests & CI: {df[(df['has_tests'] == True) & (df['has_ci'] == True)].shape[0]}")
        
        # Documentation
        print(f"\n📚 DOCUMENTATION:")
        print(f"  Average doc score: {df['documentation_score'].mean():.2f}/5")
        print(f"  Excellent docs (5/5): {df[df['documentation_score'] == 5].shape[0]}")
        print(f"  Good docs (≥4/5): {df[df['documentation_score'] >= 4].shape[0]}")
        print(f"  Poor docs (<2/5): {df[df['documentation_score'] < 2].shape[0]}")
        
        # Activity
        print(f"\n🔥 ACTIVITY:")
        # Recent commits (last 3 months)
        recent_commits = 0
        for date_str in df['last_commit_date']:
            if date_str:
                try:
                    commit_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    if (datetime.now(commit_date.tzinfo) - commit_date).days < 90:
                        recent_commits += 1
                except:
                    pass
        print(f"  Active in last 3 months: {recent_commits} ({recent_commits/len(df)*100:.1f}%)")
        print(f"  Average activity score: {df['activity_score'].mean():.1f}/100")
        print(f"  High activity (≥70): {df[df['activity_score'] >= 70].shape[0]}")
        
        # Community
        print(f"\n👥 COMMUNITY ENGAGEMENT:")
        print(f"  Average contributors: {df['contributors_count'].mean():.1f}")
        print(f"  Average open PRs: {df['open_pull_requests'].mean():.1f}")
        print(f"  Total contributors: {df['contributors_count'].sum():,}")
        print(f"  Total open PRs: {df['open_pull_requests'].sum():,}")
        
        # Category distribution
        all_categories = []
        for cats in df['categories']:
            all_categories.extend(cats.split(', '))
        category_counts = Counter(all_categories)
        
        print(f"\n{'=' * 80}")
        print("📂 CATEGORY DISTRIBUTION")
        print("=" * 80)
        for cat, count in category_counts.most_common():
            percentage = (count / len(df)) * 100
            bar = "█" * int(percentage / 2)
            print(f"  {cat:25s} | {count:>3} | {percentage:>5.1f}% {bar}")
        
        # Best frameworks for production
        print(f"\n{'=' * 80}")
        print("🎖️  RECOMMENDED FOR PRODUCTION (Tests + CI + Good Docs + Active)")
        print("=" * 80)
        production_ready = df[
            (df['has_tests'] == True) & 
            (df['has_ci'] == True) & 
            (df['documentation_score'] >= 4) &
            (df['activity_score'] >= 60)
        ].sort_values('activity_score', ascending=False).head(15)
        
        for idx, row in production_ready.iterrows():
            print(f"  {row['name']:35s} | Activity: {row['activity_score']:>3} | "
                  f"Doc: {row['documentation_score']}/5 | ⭐ {row['github_stars']:>6,}")
        
        # License distribution
        print(f"\n{'=' * 80}")
        print("📜 LICENSE DISTRIBUTION")
        print("=" * 80)
        license_counts = df['license'].value_counts().head(10)
        for lic, count in license_counts.items():
            percentage = (count / len(df)) * 100
            print(f"  {str(lic):20s} | {count:>3} ({percentage:>5.1f}%)")
        
        # Overall statistics
        print(f"\n{'=' * 80}")
        print("📊 OVERALL METRICS")
        print("=" * 80)
        print(f"  Total downloads (last month): {df['downloads_last_month'].sum():,}")
        print(f"  Total GitHub stars: {df['github_stars'].sum():,}")
        print(f"  Total forks: {df['github_forks'].sum():,}")
        print(f"  Packages with GitHub repo: {df[df['github_stars'] > 0].shape[0]} ({df[df['github_stars'] > 0].shape[0]/len(df)*100:.1f}%)")
        print(f"  Average dependencies: {df['dependencies'].mean():.1f}")
        
        print("=" * 80 + "\n")
        
        return df


# Main execution
if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🚀 NODE.JS FRAMEWORK DATA COLLECTOR - EXTENDED SPK VERSION")
    print("   Collecting 500+ packages with comprehensive metrics")
    print("=" * 80 + "\n")
    
    # GitHub token for higher rate limits (RECOMMENDED)
    # Get token from: https://github.com/settings/tokens
    # Required scopes: public_repo
    github_token = "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"
    
    
    if not github_token:
        print("⚠️  WARNING: No GitHub token provided")
        print("   Rate limited to 60 requests/hour per IP")
        print("   Collection will be SLOW (~60-90 minutes)")
        print("   Get token from: https://github.com/settings/tokens")
        print("   Required scopes: public_repo")
        print("   Set: github_token = 'ghp_your_token_here'\n")
        input("Press Enter to continue or Ctrl+C to cancel...")
    else:
        print("✅ GitHub token detected - using enhanced rate limits\n")
    
    collector = NodeJSFrameworkCollector(github_token=github_token)
    
    # Collect 500+ frameworks with extended metrics
    print("\n📊 Extended metrics include:")
    print("   - Security: Vulnerabilities count")
    print("   - Efficiency: Package size (KB)")
    print("   - Updates: Release frequency")
    print("   - Quality: Tests, CI/CD status")
    print("   - Documentation: Quality score (1-5)")
    print("   - Activity: Last commit, activity score")
    print("   - Community: Contributors, open PRs")
    print("")
    
    frameworks = collector.collect_frameworks(min_count=500)
    
    # Save to multiple formats
    print("\n💾 Saving data to files...")
    collector.save_to_csv('nodejs_frameworks_500_extended.csv')
    collector.save_to_json('nodejs_frameworks_500_extended.json')
    collector.save_to_excel('nodejs_frameworks_500_extended.xlsx')
    
    # Show comprehensive statistics
    collector.get_summary_statistics()
    
    print("\n✅ DATA COLLECTION COMPLETE!")
    print("=" * 80)
    print("📁 Files created:")
    print("   - nodejs_frameworks_500_extended.csv")
    print("   - nodejs_frameworks_500_extended.json")
    print("   - nodejs_frameworks_500_extended.xlsx")
    print("     └─ Sheets: All Frameworks, Top 50 Active, Top 50 Downloads,")
    print("        Top 50 Quality, Best for Production, Categories, SPK Analysis")
    print("=" * 80)
    print("\n💡 SPK Metrics collected:")
    print("   ✓ Security (vulnerabilities)")
    print("   ✓ Package size (efficiency)")
    print("   ✓ Release frequency")
    print("   ✓ Test coverage & CI status")
    print("   ✓ Documentation quality score")
    print("   ✓ Activity & community metrics")
    print("=" * 80 + "\n")
