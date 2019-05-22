## Патч для Imbo behat-api-extension

Да, к сожалению пока так, чтоб время съэкономить вам надо после установки компосером всех пакетов заменить файлик `ApiContext.php` 
в папке Imbo `vendor\imbo\behat-api-extension\src\Context\`.

Этот патч добавляет всего одну возможность: `Я логинюсь в слухачей как :username с паролем :password`

Это нужно чтоб токен получался и подставлялся в запрос. Пока это очень убого ибо делается два запроса, но работает.

Можете просто в этот файлик дописать код:

```php

    /**
     * Чувак входит в слухачей и его токен сохраняется в сессии
     *
     * @param string $username The username to authenticate with
     * @param string $password The password to authenticate with
     * @return self
     *
     * @Given Я логинюсь в слухачей как :username с паролем :password
     */
    public function iLoginToSluhachi($username, $password) {

        $json_body = json_encode([
            'username' => $username,
            'password' => $password
        ]) ;

        // у нас пока в base64
        $b64Token = base64_encode($json_body);
        // вставляем тело
        $this->request = $this->request->withBody(Psr7\stream_for($b64Token));
        // шлем запрос постом
        $this->setRequestPath('/login');
        $this->setRequestMethod('POST', false);
        $this->sendRequest();
        $this->requireResponse();
        $body = $this->getResponseBody();
        // выдергиваем токен и устанавливаем его для следующего запроса
        if (!$body->token){
            throw new InvalidArgumentException(
                'Нету токена в ответе при логине. Вот весь ответ: ' . json_encode($body, JSON_PRETTY_PRINT)
            );
        }
        $token = str_replace('"', '', $body->token);
        $token = str_replace("'", '', $token);
        // токен влепляем в запрос
        $this->setRequestHeader('Authorization', 'Bearer '.$token);

        return $this;
    }

	
```

