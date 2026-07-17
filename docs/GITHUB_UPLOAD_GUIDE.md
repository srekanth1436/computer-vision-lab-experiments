# Upload This Project to GitHub

## Easy website method

1. Sign in to GitHub.
2. Click **New repository**.
3. Repository name: `computer-vision-lab-experiments`
4. Choose **Public**.
5. Do not add a README, `.gitignore`, or license because they are already included.
6. Click **Create repository**.
7. On the empty repository page, click **uploading an existing file**.
8. Extract the ZIP file on your computer.
9. Open the extracted `computer-vision-lab-experiments` folder.
10. Drag all files and folders into GitHub.
11. Commit message: `Add all 40 Computer Vision lab experiments`
12. Click **Commit changes**.

## Git command method

```bash
git init
git add .
git commit -m "Add all 40 Computer Vision lab experiments"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/computer-vision-lab-experiments.git
git push -u origin main
```
