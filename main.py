import requests
import json
import time
import csv
from datetime import datetime, timedelta
import pandas as pd
from collections import Counter
import threading
from queue import Queue

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
                    time.sleep(0.3)  # Rate limiting
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
    
    def get_github_stats(self, repo_url):
        """Get GitHub statistics"""
        if not repo_url or 'github.com' not in repo_url:
            return None
        
        try:
            # Extract owner and repo from URL
            parts = repo_url.replace('https://github.com/', '').replace('git://github.com/', '').replace('.git', '').split('/')
            if len(parts) >= 2:
                owner, repo = parts[0], parts[1]
                
                # GitHub API
                url = f"https://api.github.com/repos/{owner}/{repo}"
                headers = {}
                if self.github_token:
                    headers['Authorization'] = f'token {self.github_token}'
                
                response = requests.get(url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        'stars': data.get('stargazers_count', 0),
                        'forks': data.get('forks_count', 0),
                        'watchers': data.get('watchers_count', 0),
                        'open_issues': data.get('open_issues_count', 0),
                        'last_updated': data.get('updated_at', ''),
                        'language': data.get('language', ''),
                        'size': data.get('size', 0)
                    }
        except Exception as e:
            pass
        
        return None
    
    def categorize_framework(self, package_data):
        """Categorize framework based on keywords and description"""
        description = package_data.get('description', '').lower()
        keywords = package_data.get('keywords', [])
        keywords_str = ' '.join(keywords).lower() if keywords else ''
        name = package_data.get('name', '').lower()
        
        combined_text = f"{description} {keywords_str} {name}"
        
        categories = []
        
        # Web Framework
        if any(word in combined_text for word in ['web framework', 'http server', 'web server', 'express', 'web application']):
            categories.append('Web Framework')
        
        # API Framework
        if any(word in combined_text for word in ['api', 'rest', 'restful', 'graphql', 'api framework']):
            categories.append('API Framework')
        
        # Real-time
        if any(word in combined_text for word in ['realtime', 'websocket', 'socket', 'real-time', 'ws']):
            categories.append('Real-time')
        
        # Full-stack
        if any(word in combined_text for word in ['fullstack', 'full-stack', 'isomorphic', 'universal', 'ssr', 'server-side rendering']):
            categories.append('Full-stack')
        
        # Microservices
        if any(word in combined_text for word in ['microservice', 'micro-service', 'microservices', 'distributed']):
            categories.append('Microservices')
        
        # Testing
        if any(word in combined_text for word in ['test', 'testing', 'mocha', 'jest', 'chai', 'jasmine', 'unit test']):
            categories.append('Testing')
        
        # Build Tool
        if any(word in combined_text for word in ['build', 'bundler', 'webpack', 'compiler', 'rollup', 'vite', 'build tool']):
            categories.append('Build Tool')
        
        # ORM/Database
        if any(word in combined_text for word in ['orm', 'database', 'mongodb', 'mysql', 'postgres', 'sequelize', 'typeorm']):
            categories.append('Database/ORM')
        
        # Authentication
        if any(word in combined_text for word in ['auth', 'authentication', 'passport', 'jwt', 'oauth']):
            categories.append('Authentication')
        
        # Logging
        if any(word in combined_text for word in ['log', 'logging', 'winston', 'morgan', 'logger']):
            categories.append('Logging')
        
        # Utility
        if any(word in combined_text for word in ['utility', 'helper', 'utils', 'tool']):
            categories.append('Utility')
        
        # CLI
        if any(word in combined_text for word in ['cli', 'command line', 'terminal', 'commander']):
            categories.append('CLI')
        
        return categories if categories else ['Other']
    
    def collect_frameworks(self, min_count=500):
        """Collect framework data from multiple sources"""
        print(f"Starting collection of {min_count} Node.js frameworks...")
        print("=" * 60)
        
        # Extended search terms for comprehensive coverage
        search_terms = [
            # Web & API Frameworks
            'nodejs framework',
            'express framework',
            'web framework nodejs',
            'api framework node',
            'rest framework',
            'graphql framework',
            'http server nodejs',
            'web server node',
            
            # Specific popular frameworks
            'nestjs koa fastify',
            'hapi restify loopback',
            'sails meteor adonis',
            'next nuxt remix',
            
            # By functionality
            'microservices framework',
            'real-time framework',
            'socket framework',
            'websocket node',
            'authentication framework',
            'orm framework node',
            
            # Testing & Build
            'testing framework nodejs',
            'test framework node',
            'build tool node',
            'bundler nodejs',
            
            # Database & ORM
            'database framework node',
            'orm nodejs',
            'mongodb framework',
            'sequelize typeorm',
            
            # Utilities
            'nodejs utility',
            'node helper',
            'nodejs tools',
            'middleware nodejs',
            
            # Server & Runtime
            'node server',
            'nodejs runtime',
            'node application',
            'backend framework',
            
            # Modern patterns
            'serverless framework',
            'jamstack node',
            'edge framework',
            'headless cms node',
            
            # Additional categories
            'logging framework node',
            'validation framework',
            'routing framework',
            'template engine node',
            'view engine nodejs',
            'cli framework node',
            'command line tool',
            
            # By use case
            'ecommerce framework',
            'cms framework node',
            'blog framework',
            'api gateway node',
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
            
            print(f"  → Found {new_packages} new packages")
            print(f"  → Total unique packages: {len(all_packages)}")
            
            if len(all_packages) >= min_count * 1.5:  # Get extra for filtering
                print(f"\n✓ Reached target of {min_count} packages!")
                break
            
            time.sleep(0.5)  # Rate limiting
        
        print(f"\n{'=' * 60}")
        print(f"Total unique packages found: {len(all_packages)}")
        print(f"Processing top {min(len(all_packages), min_count)} packages...")
        print(f"{'=' * 60}\n")
        
        # Sort by popularity (downloads + quality score)
        packages_to_process = all_packages[:min(len(all_packages), min_count)]
        
        # Process each package
        for idx, pkg in enumerate(packages_to_process, 1):
            name = pkg.get('name', '')
            
            if name in self.processed_names:
                continue
            
            self.processed_names.add(name)
            
            print(f"[{idx}/{len(packages_to_process)}] Processing: {name}")
            
            try:
                # Get detailed package info
                details = self.get_package_details(name)
                if not details:
                    print(f"  ✗ Failed to get details")
                    continue
                
                # Get download stats
                downloads = self.get_download_stats(name)
                
                # Get GitHub stats
                repo_url = None
                if 'repository' in details:
                    repo_info = details['repository']
                    if isinstance(repo_info, dict):
                        repo_url = repo_info.get('url', '')
                    elif isinstance(repo_info, str):
                        repo_url = repo_info
                
                github_stats = self.get_github_stats(repo_url) if repo_url else None
                
                # Get latest version info
                latest_version = details.get('dist-tags', {}).get('latest', '')
                versions = details.get('versions', {})
                version_data = versions.get(latest_version, {})
                
                # Categorize
                categories = self.categorize_framework(version_data)
                
                # Get author info
                author = details.get('author', {})
                if isinstance(author, dict):
                    author_name = author.get('name', '')
                elif isinstance(author, str):
                    author_name = author
                else:
                    author_name = ''
                
                framework_data = {
                    'name': name,
                    'version': latest_version,
                    'description': pkg.get('description', '')[:500],  # Limit length
                    'author': author_name,
                    'license': version_data.get('license', ''),
                    'keywords': ', '.join(pkg.get('keywords', [])[:10]),  # Top 10 keywords
                    'categories': ', '.join(categories),
                    'downloads_last_month': downloads,
                    'repository': repo_url,
                    'homepage': pkg.get('links', {}).get('homepage', ''),
                    'npm_url': pkg.get('links', {}).get('npm', ''),
                    'created_date': details.get('time', {}).get('created', ''),
                    'modified_date': details.get('time', {}).get('modified', ''),
                    'github_stars': github_stats.get('stars', 0) if github_stats else 0,
                    'github_forks': github_stats.get('forks', 0) if github_stats else 0,
                    'github_watchers': github_stats.get('watchers', 0) if github_stats else 0,
                    'github_issues': github_stats.get('open_issues', 0) if github_stats else 0,
                    'github_language': github_stats.get('language', '') if github_stats else '',
                    'maintainers': len(details.get('maintainers', [])),
                    'dependencies': len(version_data.get('dependencies', {})),
                    'dev_dependencies': len(version_data.get('devDependencies', {})),
                }
                
                self.frameworks.append(framework_data)
                print(f"  ✓ Success | Downloads: {downloads:,} | Stars: {github_stats.get('stars', 0) if github_stats else 0}")
                
                # Rate limiting
                if github_stats and not self.github_token:
                    time.sleep(0.8)  # Slower without token
                else:
                    time.sleep(0.2)
                    
            except Exception as e:
                print(f"  ✗ Error: {e}")
                continue
        
        print(f"\n{'=' * 60}")
        print(f"✅ Successfully collected {len(self.frameworks)} frameworks!")
        print(f"{'=' * 60}\n")
        return self.frameworks
    
    def save_to_csv(self, filename='nodejs_frameworks_500.csv'):
        """Save data to CSV file"""
        if not self.frameworks:
            print("No data to save!")
            return
        
        df = pd.DataFrame(self.frameworks)
        df.to_csv(filename, index=False, encoding='utf-8')
        print(f"✅ Data saved to {filename}")
    
    def save_to_json(self, filename='nodejs_frameworks_500.json'):
        """Save data to JSON file"""
        if not self.frameworks:
            print("No data to save!")
            return
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.frameworks, f, indent=2, ensure_ascii=False)
        print(f"✅ Data saved to {filename}")
    
    def save_to_excel(self, filename='nodejs_frameworks_500.xlsx'):
        """Save data to Excel file with multiple sheets"""
        if not self.frameworks:
            print("No data to save!")
            return
        
        try:
            df = pd.DataFrame(self.frameworks)
            
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                # Main data
                df.to_excel(writer, sheet_name='All Frameworks', index=False)
                
                # Top by downloads
                top_downloads = df.nlargest(50, 'downloads_last_month')[['name', 'downloads_last_month', 'categories', 'github_stars']]
                top_downloads.to_excel(writer, sheet_name='Top 50 Downloads', index=False)
                
                # Top by stars
                top_stars = df.nlargest(50, 'github_stars')[['name', 'github_stars', 'downloads_last_month', 'categories']]
                top_stars.to_excel(writer, sheet_name='Top 50 Stars', index=False)
                
                # Category summary
                all_categories = []
                for cats in df['categories']:
                    all_categories.extend(cats.split(', '))
                category_counts = Counter(all_categories)
                cat_df = pd.DataFrame(category_counts.most_common(), columns=['Category', 'Count'])
                cat_df.to_excel(writer, sheet_name='Categories', index=False)
            
            print(f"✅ Data saved to {filename}")
        except ImportError:
            print("⚠️  openpyxl not installed. Install with: pip install openpyxl")
    
    def get_summary_statistics(self):
        """Get summary statistics of collected data"""
        if not self.frameworks:
            return None
        
        df = pd.DataFrame(self.frameworks)
        
        print("\n" + "=" * 60)
        print("📊 SUMMARY STATISTICS")
        print("=" * 60)
        print(f"Total frameworks collected: {len(df)}")
        
        print(f"\n📈 TOP 15 BY DOWNLOADS (Last Month):")
        print("-" * 60)
        top_dl = df.nlargest(15, 'downloads_last_month')[['name', 'downloads_last_month', 'github_stars']]
        for idx, row in top_dl.iterrows():
            print(f"  {row['name']:30s} | {row['downloads_last_month']:>12,} | ⭐ {row['github_stars']:>6,}")
        
        print(f"\n⭐ TOP 15 BY GITHUB STARS:")
        print("-" * 60)
        top_stars = df.nlargest(15, 'github_stars')[['name', 'github_stars', 'downloads_last_month']]
        for idx, row in top_stars.iterrows():
            print(f"  {row['name']:30s} | ⭐ {row['github_stars']:>6,} | {row['downloads_last_month']:>12,}")
        
        # Category distribution
        all_categories = []
        for cats in df['categories']:
            all_categories.extend(cats.split(', '))
        
        category_counts = Counter(all_categories)
        
        print(f"\n📂 CATEGORY DISTRIBUTION:")
        print("-" * 60)
        for cat, count in category_counts.most_common():
            percentage = (count / len(df)) * 100
            bar = "█" * int(percentage / 2)
            print(f"  {cat:25s} | {count:>3} | {percentage:>5.1f}% {bar}")
        
        # Statistics
        print(f"\n📊 GENERAL STATISTICS:")
        print("-" * 60)
        print(f"  Total downloads (last month): {df['downloads_last_month'].sum():,}")
        print(f"  Average downloads per package: {df['downloads_last_month'].mean():,.0f}")
        print(f"  Median downloads: {df['downloads_last_month'].median():,.0f}")
        print(f"  Total GitHub stars: {df['github_stars'].sum():,}")
        print(f"  Average stars per package: {df['github_stars'].mean():,.1f}")
        print(f"  Packages with GitHub repo: {df[df['github_stars'] > 0].shape[0]}")
        
        # License distribution
        print(f"\n📜 TOP 10 LICENSES:")
        print("-" * 60)
        license_counts = df['license'].value_counts().head(10)
        for lic, count in license_counts.items():
            print(f"  {lic:20s} | {count:>3}")
        
        print("=" * 60 + "\n")
        
        return df


# Main execution
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀 NODE.JS FRAMEWORK DATA COLLECTOR (500+ packages)")
    print("=" * 60 + "\n")
    
    # Optional: Add GitHub token for higher rate limits
    # Get token from: https://github.com/settings/tokens
    github_token = None  # Replace with your token: "ghp_your_token_here"
    
    if not github_token:
        print("⚠️  No GitHub token provided. Rate limited to 60 requests/hour.")
        print("   Get token from: https://github.com/settings/tokens")
        print("   Set: github_token = 'your_token_here'\n")
    
    collector = NodeJSFrameworkCollector(github_token=github_token)
    
    # Collect 500+ frameworks
    frameworks = collector.collect_frameworks(min_count=500)
    
    # Save to multiple formats
    print("\n💾 Saving data to files...")
    collector.save_to_csv('nodejs_frameworks_500.csv')
    collector.save_to_json('nodejs_frameworks_500.json')
    collector.save_to_excel('nodejs_frameworks_500.xlsx')
    
    # Show statistics
    collector.get_summary_statistics()
    
    print("\n✅ DATA COLLECTION COMPLETE!")
    print("=" * 60)
    print("📁 Files created:")
    print("   - nodejs_frameworks_500.csv")
    print("   - nodejs_frameworks_500.json")
    print("   - nodejs_frameworks_500.xlsx")
    print("=" * 60 + "\n")