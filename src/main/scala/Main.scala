import java.time.Duration
import org.openqa.selenium.By
import org.openqa.selenium.firefox.FirefoxDriver
import org.openqa.selenium.support.ui.WebDriverWait
import sys.process._
import java.net._
import java.io._
import scala.collection.JavaConverters

object WillysGptDataScrapper {

  val folder = "aggregate/receipts"

  def downloadFile(url: String, destination: String): Unit = {
    (new URL(url) #> new File(destination)).!
    ()
  }

  def writeTxtFile(txt: String, destination: String): Unit = {
    val pw = new PrintWriter(new File(destination))
    pw.write(txt)
    pw.close
  }

  def cleanup(directory: String) = {
    val file = new File(directory)
    if (file.isDirectory) then
      file.listFiles.foreach(_.delete)
    else
      throw RuntimeException("folder is configured wrong")
  }

  def main(args: Array[String]): Unit = {
    System.setProperty(
      "webdriver.gecko.driver",
      "/opt/homebrew/bin/geckodriver"
    )
    val driver = new FirefoxDriver
    driver.manage.window.maximize()
    driver.manage.deleteAllCookies()
    driver.manage.timeouts.pageLoadTimeout(Duration.ofSeconds(40))
    driver.manage.timeouts.implicitlyWait(Duration.ofSeconds(30))
    driver.get("https://www.willys.se/anvandare/inloggning")

    cleanup(folder)

    Thread.sleep(3000)
    val declineCookies =
      driver.findElement(By.id("onetrust-reject-all-handler"))
    declineCookies.click()

    Thread.sleep(500)
    val userNameInput = driver.findElement(By.className("sc-827e1384-0"))
    userNameInput.sendKeys(System.getenv("WILLYS_USERNAME"))

    Thread.sleep(500)
    val passwordInput =
      driver.findElements(By.className("sc-827e1384-0")).get(1)
    passwordInput.sendKeys(System.getenv("WILLYS_PASSWORD"))

    Thread.sleep(1000)
    val login = driver.findElements(By.className("sc-dfa63f22-0")).get(1)
    login.click()

    println("LOG: Logged in")

    Thread.sleep(2000)
    val userId = driver.findElement(By.className("sc-a3164ebe-0"))
    val userName = userId.getText()
    writeTxtFile(userName, s"$folder/userName.txt")
    userId.click()

    Thread.sleep(500)
    val purchases = driver.findElement(By.ByPartialLinkText("Mina köp"))
    purchases.click()

    println("LOG: Go to receipts page")

    Thread.sleep(1000)

    val calender = driver.findElements(By.className("sc-fde63b83-0")).get(3)
    calender.click()
    Thread.sleep(500)

    val backwards = driver.findElement(By.className("rdp-nav_icon"))
    backwards.click()
    Thread.sleep(500)

    val numberOne = driver.findElements(By.className("rdp-day")).get(3)
    numberOne.click()
    Thread.sleep(500)

    val choose = driver.findElements(By.className("sc-dfa63f22-0")).get(3)
    choose.click()
    Thread.sleep(1000)

    println("LOG: Updated calender")

    val showMore = driver.findElement(By.className("sc-67897609-2"))
    showMore.click()
    Thread.sleep(1000)
    driver.executeScript("window.scrollTo(0, document.body.scrollHeight)")
    Thread.sleep(1000)

    println("LOG: Force load more receipts")

    val purchaseTable = driver.findElement(By.className("sc-139d58d8-1"))
    val allPurchases = purchaseTable.findElements(By.className("sc-f1f2eb33-0"))
    val recieptLinks =
      for reciept <- JavaConverters.asScalaBuffer(allPurchases).toSeq
      yield reciept.getAttribute("href")
    
    for link <- recieptLinks.filter(_ != null)
        params = new URI(link).getQuery.split('&').collect { case s"$key=$value" => key -> value }.toMap
        filePath = s"${folder}/${params("date")}-${params("storeId")}-${params("memberCardNumber")}.pdf"
      yield downloadFile(link, filePath)
    
    println("downloaded reciepts")
 
    Thread.sleep(1000000)
    driver.quit()
  }
}
